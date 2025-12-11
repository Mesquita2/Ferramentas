import io
import streamlit as st
import pandas as pd
import numpy as np
from typing import List, Dict

# ---------------------------
# Config
# ---------------------------
st.set_page_config(page_title="Tratamento de Notas - Simulado", layout="wide")
EXCLUIR_PADRAO = r'(?:Projeto de Extensão|Seminários|Liga dos Campeões|Estágio|TCC|Trabalho de Conclusão de Curso)'

# ---------------------------
# Util: carregar excel com cache
# ---------------------------
@st.cache_data
def carregar_excel_bytes(uploaded_file) -> pd.DataFrame:
    """Carrega um arquivo excel (UploadedFile) para DataFrame"""
    try:
        return pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Erro ao carregar arquivo {getattr(uploaded_file, 'name', '')}: {e}")
        return pd.DataFrame()

# ---------------------------
# Funções de preparação e cálculo
# ---------------------------
def preparar_base_alunos(df_alunos_raw: pd.DataFrame) -> pd.DataFrame:
    """Prepara a base de alunos: remove padrões e renomeia colunas se necessário."""
    df = df_alunos_raw.copy()
    # Sevier para renomear se as colunas estiverem em nomes alternativos
    rename_map = {}
    if 'NOMEDISCIPLINA' in df.columns and 'DISCIPLINA' not in df.columns:
        rename_map['NOMEDISCIPLINA'] = 'DISCIPLINA'
    if 'NOMECURSO' in df.columns and 'CURSO' not in df.columns:
        rename_map['NOMECURSO'] = 'CURSO'
    if 'NOMEALUNO' in df.columns and 'ALUNO' not in df.columns:
        rename_map['NOMEALUNO'] = 'ALUNO'
    if rename_map:
        df = df.rename(columns=rename_map)

    # Filtrar padroes indesejados
    if 'DISCIPLINA' in df.columns:
        df = df[~df['DISCIPLINA'].astype(str).str.contains(EXCLUIR_PADRAO, case=False, na=False)].reset_index(drop=True)

    # garantir colunas básicas existam
    for c in ['CURSO', 'TURMADISC', 'RA', 'ALUNO', 'DISCIPLINA']:
        if c not in df.columns:
            df[c] = np.nan

    # padronizar RA
    df['RA'] = df['RA'].astype(str).fillna('').apply(lambda x: x.zfill(7) if x.strip() != '' else x)
    return df

def calcula_qtd_questoes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula numero de questoes por aluno seguindo regras:
      - Administração: NUMCREDITOSCOB 4 -> 12, 2 -> 6
      - Direito: idem
      - Engenharia: por aluno 30 se tiver TURMADISC == '037C', senão 60 (não soma por disciplina)
    Retorna df com colunas ['ALUNO','RA','Questoes'] (RA zeropadded)
    """
    df = df.copy()
    df['Questoes'] = 0

    credito_to_questoes = {4: 12, 2: 6}

    mask_adm = df['CURSO'] == 'Bacharelado em Administração de Empresas'
    mask_dir = df['CURSO'] == 'Bacharelado em Direito'
    mask_eng = df['CURSO'] == 'Bacharelado em Engenharia de Software'

    if 'NUMCREDITOSCOB' in df.columns:
        df.loc[mask_adm, 'Questoes'] = df.loc[mask_adm, 'NUMCREDITOSCOB'].map(credito_to_questoes).fillna(0).astype(int)
        df.loc[mask_dir, 'Questoes'] = df.loc[mask_dir, 'NUMCREDITOSCOB'].map(credito_to_questoes).fillna(0).astype(int)

    # Engenharia: determinar por aluno
    df.loc[mask_eng, 'TURMADISC'] = df.loc[mask_eng, 'TURMADISC'].astype(str).str.upper().str.strip()
    alunos_eng = df.loc[mask_eng, ['ALUNO', 'RA', 'TURMADISC']].drop_duplicates()
    if not alunos_eng.empty:
        alunos_eng['Tem_037C'] = alunos_eng['TURMADISC'].fillna('').apply(lambda x: x.strip().upper() == '037C')
        questoes_por_aluno = alunos_eng.groupby(['ALUNO', 'RA'])['Tem_037C'].any().reset_index()
        questoes_por_aluno['Questoes'] = questoes_por_aluno['Tem_037C'].apply(lambda x: 30 if x else 60)
        questoes_por_aluno = questoes_por_aluno.drop(columns='Tem_037C')
    else:
        questoes_por_aluno = pd.DataFrame(columns=['ALUNO','RA','Questoes'])

    # Zerar engenharia na base original para não somar por disciplina
    df.loc[mask_eng, 'Questoes'] = 0

    # Somar ADM e DIR por aluno
    if not df.loc[~mask_eng].empty and 'ALUNO' in df.columns and 'RA' in df.columns:
        df_adm_dir = df.loc[~mask_eng].groupby(['ALUNO', 'RA'])['Questoes'].sum().reset_index()
    else:
        df_adm_dir = pd.DataFrame(columns=['ALUNO','RA','Questoes'])

    # Concatenar e agrupar
    df_final = pd.concat([df_adm_dir, questoes_por_aluno], ignore_index=True, sort=False)
    if not df_final.empty:
        df_final = df_final.groupby(['ALUNO','RA'], as_index=False)['Questoes'].sum()
        df_final['RA'] = df_final['RA'].astype(str).str.zfill(7)
    else:
        df_final = pd.DataFrame(columns=['ALUNO','RA','Questoes'])

    return df_final

def ajustar_dataframe_zipgrade(df_zip: pd.DataFrame) -> pd.DataFrame:
    """
    Ajustes do DataFrame ZipGrade: padroniza RA, nomes e remove linhas inválidas.
    Espera colunas como: 'Student ID' ou 'RA', 'Student First Name', 'Student Last Name'
    """
    df = df_zip.copy()
    # definir RA a partir de Student ID ou RA
    if 'Student ID' in df.columns:
        df['Student ID'] = df['Student ID'].astype(str).fillna('').apply(lambda x: x.zfill(7) if x.strip() != '' else x)
        df.rename(columns={'Student ID': 'RA'}, inplace=True)
    elif 'RA' in df.columns:
        df['RA'] = df['RA'].astype(str).fillna('').apply(lambda x: x.zfill(7) if x.strip() != '' else x)
    else:
        # criar RA vazio para não quebrar
        df['RA'] = ''

    # montar nome do aluno
    first = df.get('Student First Name', pd.Series(['']*len(df)))
    last  = df.get('Student Last Name', pd.Series(['']*len(df)))
    df['NOMEALUNO'] = (first.fillna('') + ' ' + last.fillna('')).str.strip()
    # filtrar linhas sem RA ou sem nome
    df = df[(df['RA'].astype(str) != '') & (df['NOMEALUNO'] != '')].copy()
    # garantir colunas de pontos e earned existam
    if 'Earned Points' not in df.columns:
        df['Earned Points'] = 0
    if 'Possible Points' not in df.columns:
        df['Possible Points'] = np.nan
    df['RA'] = df['RA'].astype(str).str.zfill(7)
    return df

def detectar_colunas_zipgrade(df: pd.DataFrame) -> Dict[str, List[str]]:
    """
    Detecta:
      - points_cols: '#{n} Points Earned'
      - response_cols: '#{n} Student Response' ou '#{n} Student Answer'
    Retorna dicionario.
    """
    points_cols = [c for c in df.columns if c.startswith('#') and 'Points Earned' in c]
    response_cols = [c for c in df.columns if c.startswith('#') and ('Student Response' in c or 'Student Answer' in c)]
    # fallback: se nao houver response_cols, usar points_cols para estimar respostas
    if not response_cols and points_cols:
        response_cols = points_cols.copy()
    return {'points_cols': points_cols, 'response_cols': response_cols}

def aplicar_anuladas_e_calcular_notas(
    df_zip: pd.DataFrame,
    df_alunos_base: pd.DataFrame,
    questoes_anuladas: List[int],
    alunos_ajustar: Dict[str, int],
    prova: str,
    etapa: str,
    codetapa: int,
    codprova: int,
    tipoetapa: str
):
    """
    Aplica anuladas e calcula NOTAS.
    Retorna: df_final (por aluno), df_discrepancias (questoes vs possible points), df_zip_processado (com notas por linha)
    """
    df_base_local = df_alunos_base.copy()
    df_base_local['RA'] = df_base_local['RA'].astype(str).str.zfill(7)

    # limitar base aos RAs presentes
    presentes = df_zip['RA'].astype(str).str.zfill(7).unique()
    df_base_local = df_base_local[df_base_local['RA'].isin(presentes)].copy()

    # calcular questoess esperadas
    df_questoes = calcula_qtd_questoes(df_base_local)

    # garantir RA formatado no zip
    df_zip['RA'] = df_zip['RA'].astype(str).str.zfill(7)

    col_info = detectar_colunas_zipgrade(df_zip)
    points_cols = col_info['points_cols']
    response_cols = col_info['response_cols']

    # soma possible points por RA
    df_simulado_pontos = df_zip.groupby('RA')['Possible Points'].sum().reset_index().rename(columns={'Possible Points': 'PontosSimulado'})

    # merge para validação
    df_questoes['RA'] = df_questoes['RA'].astype(str).str.zfill(7)
    df_simulado_pontos['RA'] = df_simulado_pontos['RA'].astype(str).str.zfill(7)
    df_validacao = pd.merge(df_questoes, df_simulado_pontos, on='RA', how='left')
    df_validacao['DiferencaQuestoes'] = df_validacao['Questoes'] - df_validacao['PontosSimulado'].fillna(0)
    df_discrepancias = df_validacao[df_validacao['DiferencaQuestoes'] != 0]

    # preparar earned/possible
    df_zip['Earned Points Original'] = df_zip.get('Earned Points', 0).fillna(0).astype(float)

    # ajustar Possible Points (por linha) com alunos_ajustar (map RA->qtdNaoRespondidas)
    if alunos_ajustar:
        df_zip['Possible Points Ajustado'] = df_zip.apply(
            lambda r: (r['Possible Points'] - alunos_ajustar.get(r['RA'], 0)) if pd.notna(r['Possible Points']) else r['Possible Points'],
            axis=1
        )
    else:
        df_zip['Possible Points Ajustado'] = df_zip['Possible Points']

    # evitar zeros
    df_zip['Possible Points Ajustado'] = df_zip['Possible Points Ajustado'].replace(0, np.nan)

    # calcular quantas respostas (nao NaN) por aluno usando response_cols
    if response_cols:
        # contagem por linha do número de respostas registradas
        respostas_por_linha = df_zip[response_cols].notna().sum(axis=1)
        # agora soma por RA -> total de respostas registradas por aluno (todas as linhas somadas)
        respondidas_por_ra = df_zip.assign(respostas_por_linha=respostas_por_linha).groupby('RA')['respostas_por_linha'].sum().to_dict()
    else:
        # se não há colunas de resposta, considerar que todos responderam nada (0)
        respondidas_por_ra = {ra: 0 for ra in df_zip['RA'].unique()}

    # inicializar bonus_total por RA
    unique_ras = np.unique(df_zip['RA'].astype(str))
    bonus_total = pd.Series(0, index=unique_ras, dtype=int)

    # Para cada questão anulada, somar bonus apenas para linhas em que:
    # (col == 0) and (col notna) and (aluno respondeu ao menos 1 questao no conjunto)
    for q in questoes_anuladas:
        coluna = f"#{q} Points Earned"
        if coluna in df_zip.columns:
            ganhos_linha = (
                (df_zip[coluna] == 0) &         # nota zero (errou)
                (df_zip[coluna].notna()) &      # não é NaN -> respondeu
                (df_zip['RA'].map(lambda ra: respondidas_por_ra.get(ra, 0)) > 0)  # aluno respondeu ao menos 1 questão
            ).astype(int)
            # agrupar por RA e somar
            bonus = pd.Series(ganhos_linha.values, index=df_zip['RA'].astype(str)).groupby(level=0).sum()
            bonus_total = bonus_total.add(bonus, fill_value=0).astype(int)

    # mapear bonus para linhas
    df_zip['Bonus Anuladas'] = df_zip['RA'].map(bonus_total).fillna(0).astype(int)

    # calcular nota final por linha e depois agregar por RA
    df_zip['Earned Points Final'] = df_zip['Earned Points Original'] + df_zip['Bonus Anuladas']
    df_zip['NOTAS'] = np.minimum((df_zip['Earned Points Final'] * 1.25) / df_zip['Possible Points Ajustado'], 1).fillna(0) * 10

    # Agregar NOTAS por RA -> média (mantendo compatibilidade com lógica prévia)
    df_notas_por_ra = df_zip.groupby('RA', as_index=False).agg({'NOTAS': 'mean'})

    # Merge com base de alunos (para colunas adicionais)
    df_final = pd.merge(df_base_local, df_notas_por_ra, on='RA', how='left')

    # adicionar metadados
    df_final['CODETAPA'] = codetapa
    df_final['CODPROVA'] = codprova
    df_final['TIPOETAPA'] = tipoetapa
    df_final['PROVA'] = prova
    df_final['ETAPA'] = etapa

    # selecionar colunas de saída padronizadas (apenas as que existem)
    colunas = ['CODCOLIGADA', 'CURSO', 'TURMADISC', 'IDTURMADISC', 'DISCIPLINA',
               'RA', 'ALUNO', 'ETAPA', 'PROVA', 'TIPOETAPA', 'CODETAPA', 'CODPROVA', 'NOTAS']
    existentes = [c for c in colunas if c in df_final.columns]
    df_final = df_final[existentes]

    # arredondar notas
    if 'NOTAS' in df_final.columns:
        df_final['NOTAS'] = pd.to_numeric(df_final['NOTAS'], errors='coerce').round(2)

    return df_final, df_discrepancias, df_zip

# ---------------------------
# Função principal: carregar() (ponto de entrada para pages)
# ---------------------------
def carregar():
    """
    Função de entrada que renderiza TODA a interface Streamlit (upload, filtros, cálculos e downloads).
    Não retorna nada — mesma lógica de uso pelas pages do seu projeto.
    """
    st.title("Tratamento de Notas - Simulado (Versão Integrada)")

    # verificar session_state com base de alunos
    if "dados" not in st.session_state or "alunosxdisciplinas" not in st.session_state["dados"]:
        st.error("`st.session_state['dados']['alunosxdisciplinas']` não encontrado. Carregue os dados de alunos no session_state antes de executar.")
        return

    df_alunos_raw = st.session_state["dados"].get("alunosxdisciplinas")
    df_base = preparar_base_alunos(df_alunos_raw)

    # filtros: curso, turma, disciplinas
    cursos_disponiveis = sorted(df_base['CURSO'].dropna().unique())
    if not cursos_disponiveis:
        st.error("Nenhum curso disponível na base de alunos.")
        return

    curso_selecionado = st.selectbox("Selecione o curso para filtrar as disciplinas:", options=cursos_disponiveis)

    turmas_disponiveis = sorted(df_base[df_base['CURSO'] == curso_selecionado]['TURMADISC'].dropna().unique())
    turma_selecionada = st.multiselect("Selecione a(s) Turma(s):", options=turmas_disponiveis)

    if not turma_selecionada:
        st.info("Selecione ao menos uma turma para continuar.")
        return

    # disciplinas disponiveis (após filtros)
    disciplinas_disponiveis = sorted(
        df_base[
            (df_base['CURSO'] == curso_selecionado) &
            (df_base['TURMADISC'].isin(turma_selecionada))
        ]['DISCIPLINA'].dropna().unique()
    )

    disciplinas_excluidas = st.multiselect("Disciplinas que NÃO são aplicadas no Simulado:", options=disciplinas_disponiveis, default=[])

    # upload múltiplo
    uploaded_files = st.file_uploader("Envie um ou mais arquivos de notas (Excel - ZipGrade)", type=["xlsx"], accept_multiple_files=True)
    if not uploaded_files:
        st.info("Envie pelo menos um arquivo Excel com as notas (ZipGrade).")
        return

    # carregar e concatenar
    lista_dfs = []
    for uf in uploaded_files:
        df_temp = carregar_excel_bytes(uf)
        if not df_temp.empty:
            lista_dfs.append(df_temp)
    if not lista_dfs:
        st.error("Nenhum arquivo válido carregado.")
        return

    df_original = pd.concat(lista_dfs, ignore_index=True, sort=False)
    st.subheader("Dados Originais (consolidados)")
    st.dataframe(df_original.head(200))

    # ajustar zipgrade
    df_ajustado = ajustar_dataframe_zipgrade(df_original)

    # detectar colunas e contar NaNs por linha (respostas)
    col_info = detectar_colunas_zipgrade(df_ajustado)
    response_cols = col_info['response_cols']
    points_cols = col_info['points_cols']

    if response_cols:
        df_ajustado['Nao_Respondidas'] = df_ajustado[response_cols].isna().sum(axis=1)
    else:
        df_ajustado['Nao_Respondidas'] = 0

    # exibir alunos que deixaram questões em branco (NaN)
    df_nulos = df_ajustado[df_ajustado['Nao_Respondidas'] > 0][['RA', 'NOMEALUNO', 'Nao_Respondidas']].copy()
    if not df_nulos.empty:
        st.subheader("Alunos com questões não respondidas (NaN)")
        st.warning(f"{len(df_nulos)} linhas com questões não respondidas.")
        st.dataframe(df_nulos.sort_values("Nao_Respondidas", ascending=False))

    # selecionar alunos para ajustar Possible Points (desconsiderar NaNs)
    selecionados_nomes = st.multiselect(
        "Selecionar alunos (por nome) para ajustar Possible Points (desconsiderar NaNs):",
        options=df_nulos['NOMEALUNO'].unique().tolist()
    )

    # montar mapeamento RA -> qtd de NaNs para ajustar
    alunos_ajustar = {}
    if selecionados_nomes:
        df_sel = df_nulos[df_nulos['NOMEALUNO'].isin(selecionados_nomes)].copy()
        # somar NaNs por RA (caso haja múltiplas linhas)
        mapeamento = df_sel.groupby('RA')['Nao_Respondidas'].sum().to_dict()
        alunos_ajustar = {str(k).zfill(7): int(v) for k, v in mapeamento.items()}

    # parametros da prova
    etapa = "P3"
    prova = st.selectbox('Selecione o tipo de prova', ['Prova', 'Recuperação'])
    tipoetapa = 'N'
    codetapa = 3
    codprova = 1 if prova == "Prova" else 2

    questoes_anuladas_input = st.text_input("Informe questões anuladas (separadas por vírgula):", value="")
    questoes_anuladas = [int(q.strip()) for q in questoes_anuladas_input.split(",") if q.strip().isdigit()]

    # botao calcular
    if st.button("Calcular Notas com Anulações"):
        with st.spinner("Processando..."):
            # filtrar base alunos por curso/turma e excluir disciplinas
            df_base_filtrada = df_base[
                (df_base['CURSO'] == curso_selecionado) &
                (df_base['TURMADISC'].isin(turma_selecionada)) &
                (~df_base['DISCIPLINA'].isin(disciplinas_excluidas))
            ].copy()

            df_final, df_discrepancias, df_zip_processado = aplicar_anuladas_e_calcular_notas(
                df_zip=df_ajustado,
                df_alunos_base=df_base_filtrada,
                questoes_anuladas=questoes_anuladas,
                alunos_ajustar=alunos_ajustar,
                prova=prova,
                etapa=etapa,
                codetapa=codetapa,
                codprova=codprova,
                tipoetapa=tipoetapa
            )

        # exibir discrepancias
        if not df_discrepancias.empty:
            st.subheader("Discrepâncias entre questões esperadas e pontos do simulado")
            st.warning("Alguns alunos têm diferença entre Questoes esperadas e Pontos do Simulado. Ajuste manualmente se necessário.")
            st.dataframe(df_discrepancias)

        st.subheader("Notas Finais (por aluno)")
        st.dataframe(df_final)

        # formatar NOTAS BR
        if 'NOTAS' in df_final.columns:
            df_final['NOTAS'] = df_final['NOTAS'].apply(lambda x: f"{x:.2f}".replace('.', ',') if pd.notnull(x) else '')

        # download geral (TXT)
        output = io.BytesIO()
        df_final.to_csv(output, index=False, sep=';', encoding='utf-8', header=False)
        output.seek(0)

        classe = df_final['TURMADISC'].iloc[0] if 'TURMADISC' in df_final.columns and not df_final.empty else "sem_classe"
        st.download_button(
            label="⬇ Baixar Notas Tratadas (TXT Geral)",
            data=output,
            file_name=f"{classe}_{prova}.txt",
            mime="text/plain"
        )

        # download individual por aluno
        st.subheader("Baixar TXT individual por aluno")
        for ra, df_aluno in df_final.groupby("RA"):
            output_individual = io.BytesIO()
            df_aluno.to_csv(output_individual, index=False, sep=';', encoding='utf-8')
            output_individual.seek(0)

            nome_aluno = str(df_aluno["ALUNO"].iloc[0]) if "ALUNO" in df_aluno.columns else ra
            nome_aluno_sanitizado = nome_aluno.replace(" ", "_")
            file_name = f"{nome_aluno_sanitizado}_{ra}_{prova}.txt"

            st.download_button(
                label=f"⬇ {nome_aluno} (RA: {ra})",
                data=output_individual,
                file_name=file_name,
                mime="text/plain"
            )

# ---------------------------
# Executa quando este arquivo é carregado diretamente
# ---------------------------
if __name__ == "__main__":
    carregar()
