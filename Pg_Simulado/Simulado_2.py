import io
import streamlit as st
import pandas as pd
import numpy as np
from typing import List, Dict

# ---------------------------
# Config
# ---------------------------
st.set_page_config(page_title="Tratamento de Notas - Simulado", layout="wide")
EXCLUIR_PADRAO = r'(?:Projeto de Extensão|Seminários|Liga dos Campeões|Estágio|TCC|Trabalho de Conclusão de Curso|Métodologia da Pesquisa|Métodologia)'

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
    rename_map = {}
    if 'NOMEDISCIPLINA' in df.columns and 'DISCIPLINA' not in df.columns:
        rename_map['NOMEDISCIPLINA'] = 'DISCIPLINA'
    if 'NOMECURSO' in df.columns and 'CURSO' not in df.columns:
        rename_map['NOMECURSO'] = 'CURSO'
    if 'NOMEALUNO' in df.columns and 'ALUNO' not in df.columns:
        rename_map['NOMEALUNO'] = 'ALUNO'
    if rename_map:
        df = df.rename(columns=rename_map)

    if 'DISCIPLINA' in df.columns:
        df = df[~df['DISCIPLINA'].astype(str).str.contains(EXCLUIR_PADRAO, case=False, na=False)].reset_index(drop=True)

    for c in ['CURSO', 'TURMADISC', 'RA', 'ALUNO', 'DISCIPLINA']:
        if c not in df.columns:
            df[c] = np.nan

    df['RA'] = df['RA'].astype(str).fillna('').apply(lambda x: x.zfill(7) if x.strip() != '' else x)
    return df

def ajustar_dataframe_zipgrade(df_zip: pd.DataFrame) -> pd.DataFrame:
    """
    Ajustes do DataFrame ZipGrade: padroniza RA, nomes e remove linhas inválidas.
    """
    df = df_zip.copy()
    if 'Student ID' in df.columns:
        df['Student ID'] = df['Student ID'].astype(str).fillna('').apply(lambda x: x.zfill(7) if x.strip() != '' else x)
        df.rename(columns={'Student ID': 'RA'}, inplace=True)
    elif 'RA' in df.columns:
        df['RA'] = df['RA'].astype(str).fillna('').apply(lambda x: x.zfill(7) if x.strip() != '' else x)
    else:
        df['RA'] = ''

    first = df.get('Student First Name', pd.Series(['']*len(df)))
    last  = df.get('Student Last Name', pd.Series(['']*len(df)))
    df['NOMEALUNO'] = (first.fillna('') + ' ' + last.fillna('')).str.strip()

    df = df[(df['RA'].astype(str) != '') & (df['NOMEALUNO'] != '')].copy()

    if 'Earned Points' not in df.columns:
        df['Earned Points'] = 0
    if 'Possible Points' not in df.columns:
        df['Possible Points'] = np.nan
    df['RA'] = df['RA'].astype(str).str.zfill(7)
    return df

def detectar_colunas_zipgrade(df: pd.DataFrame) -> Dict[str, List[str]]:
    """
    Detecta pontos e respostas no DataFrame (por arquivo).
    """
    points_cols = [c for c in df.columns if c.startswith('#') and 'Points Earned' in c]
    response_cols = [c for c in df.columns if c.startswith('#') and ('Student Response' in c or 'Student Answer' in c)]
    if not response_cols and points_cols:
        response_cols = points_cols.copy()
    return {'points_cols': points_cols, 'response_cols': response_cols}

def aplicar_anuladas_e_calcular_notas(
    df_zip_all: pd.DataFrame,
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
    Recebe df_zip_all (concat de todos os arquivos; cada linha tem coluna 'Questoes_Prova' e 'SourceFile').
    Calcula bônus, NOTAS e retorna df_final, df_discrepancias, df_zip_all_processado.
    """
    # base local apenas com RAs presentes no zip
    df_base_local = df_alunos_base.copy()
    df_base_local['RA'] = df_base_local['RA'].astype(str).str.zfill(7)
    presentes = df_zip_all['RA'].astype(str).str.zfill(7).unique()
    df_base_local = df_base_local[df_base_local['RA'].isin(presentes)].copy()

    # Construir df_questoes a partir da coluna 'Questoes_Prova' no df_zip_all
    # Para cada RA, pegar valor único (já validado antes) -> Questoes
    df_questoes = df_zip_all.groupby('RA')['Questoes_Prova'].first().reset_index().rename(columns={'Questoes_Prova': 'Questoes'})
    df_questoes['RA'] = df_questoes['RA'].astype(str).str.zfill(7)

    # soma possible points por RA (ajustado por alunos_ajustar)
    df_zip_all['Possible Points Ajustado'] = df_zip_all['Possible Points']
    if alunos_ajustar:
        df_zip_all['Possible Points Ajustado'] = df_zip_all.apply(
            lambda r: (r['Possible Points'] - alunos_ajustar.get(r['RA'], 0)) if pd.notna(r['Possible Points']) else r['Possible Points'],
            axis=1
        )
    df_zip_all['Possible Points Ajustado'] = df_zip_all['Possible Points Ajustado'].replace(0, np.nan)

    df_simulado_pontos = df_zip_all.groupby('RA')['Possible Points Ajustado'].sum().reset_index().rename(columns={'Possible Points Ajustado': 'PontosSimulado'})

    # Merge para validação: Questoes (do Zip) x PontosSimulado
    df_validacao = pd.merge(df_questoes, df_simulado_pontos, on='RA', how='left')
    df_validacao['DiferencaQuestoes'] = df_validacao['Questoes'] - df_validacao['PontosSimulado'].fillna(0)
    df_discrepancias = df_validacao[df_validacao['DiferencaQuestoes'] != 0]

    # preparar earned points
    df_zip_all['Earned Points Original'] = df_zip_all.get('Earned Points', 0).fillna(0).astype(float)

    # detectar colunas globais de pontos e respostas no df concatenado
    points_cols_all = [c for c in df_zip_all.columns if c.startswith('#') and 'Points Earned' in c]
    response_cols_all = [c for c in df_zip_all.columns if c.startswith('#') and ('Student Response' in c or 'Student Answer' in c)]
    if not response_cols_all and points_cols_all:
        response_cols_all = points_cols_all.copy()

    # contagem de respostas por linha (usar response_cols_all)
    if response_cols_all:
        respostas_por_linha = df_zip_all[response_cols_all].notna().sum(axis=1)
        df_zip_all = df_zip_all.assign(respostas_por_linha=respostas_por_linha)
        respondidas_por_ra = df_zip_all.groupby('RA')['respostas_por_linha'].sum().to_dict()
    else:
        respondidas_por_ra = {ra: 0 for ra in df_zip_all['RA'].unique()}

    # calcular bonus por RA usando as colunas '#{q} Points Earned' existentes
    unique_ras = np.unique(df_zip_all['RA'].astype(str))
    bonus_total = pd.Series(0, index=unique_ras, dtype=int)

    for q in questoes_anuladas:
        coluna = f"#{q} Points Earned"
        if coluna in df_zip_all.columns:
            ganhos_linha = (
                (df_zip_all[coluna] == 0) &
                (df_zip_all[coluna].notna()) &
                (df_zip_all['RA'].map(lambda ra: respondidas_por_ra.get(ra, 0)) > 0)
            ).astype(int)
            bonus = pd.Series(ganhos_linha.values, index=df_zip_all['RA'].astype(str)).groupby(level=0).sum()
            bonus_total = bonus_total.add(bonus, fill_value=0).astype(int)

    df_zip_all['Bonus Anuladas'] = df_zip_all['RA'].map(bonus_total).fillna(0).astype(int)
    df_zip_all['Earned Points Final'] = df_zip_all['Earned Points Original'] + df_zip_all['Bonus Anuladas']
    df_zip_all['NOTAS'] = np.minimum((df_zip_all['Earned Points Final'] * 1.25) / df_zip_all['Possible Points Ajustado'], 1).fillna(0) * 10

    # Agregar NOTAS por RA -> média (compatibilidade)
    df_notas_por_ra = df_zip_all.groupby('RA', as_index=False).agg({'NOTAS': 'mean'})

    df_final = pd.merge(df_base_local, df_notas_por_ra, on='RA', how='left')

    df_final['CODETAPA'] = codetapa
    df_final['CODPROVA'] = codprova
    df_final['TIPOETAPA'] = tipoetapa
    df_final['PROVA'] = prova
    df_final['ETAPA'] = etapa

    colunas = ['CODCOLIGADA', 'CURSO', 'TURMADISC', 'IDTURMADISC', 'DISCIPLINA',
               'RA', 'ALUNO', 'ETAPA', 'PROVA', 'TIPOETAPA', 'CODETAPA', 'CODPROVA', 'NOTAS']
    existentes = [c for c in colunas if c in df_final.columns]
    df_final = df_final[existentes]

    if 'NOTAS' in df_final.columns:
        df_final['NOTAS'] = pd.to_numeric(df_final['NOTAS'], errors='coerce').round(2)

    return df_final, df_discrepancias, df_zip_all

# ---------------------------
# Função principal: carregar()
# ---------------------------
def carregar():
    st.title("Tratamento de Notas - Simulado (ZipGrade como única fonte)")

    # verificar session_state com base de alunos
    if "dados" not in st.session_state or "alunosxdisciplinas" not in st.session_state["dados"]:
        st.error("`st.session_state['dados']['alunosxdisciplinas']` não encontrado. Carregue os dados de alunos no session_state antes de executar.")
        return

    df_alunos_raw = st.session_state["dados"].get("alunosxdisciplinas")
    df_base = preparar_base_alunos(df_alunos_raw)

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

    disciplinas_disponiveis = sorted(
        df_base[
            (df_base['CURSO'] == curso_selecionado) &
            (df_base['TURMADISC'].isin(turma_selecionada))
        ]['DISCIPLINA'].dropna().unique()
    )

    disciplinas_excluidas = st.multiselect("Disciplinas que NÃO são aplicadas no Simulado:", options=disciplinas_disponiveis, default=[])

    uploaded_files = st.file_uploader("Envie um ou mais arquivos de notas (Excel - ZipGrade)", type=["xlsx"], accept_multiple_files=True)
    if not uploaded_files:
        st.info("Envie pelo menos um arquivo Excel com as notas (ZipGrade).")
        return

    # Processar cada arquivo separadamente e detectar quantidade de questões por arquivo
    lista_dfs = []
    ra_counts_map: Dict[str, List[Dict[str, int]]] = {}  # RA -> list of {'file': name, 'count': n}
    for uf in uploaded_files:
        df_temp = carregar_excel_bytes(uf)
        if df_temp.empty:
            continue
        df_temp_adj = ajustar_dataframe_zipgrade(df_temp)
        col_info = detectar_colunas_zipgrade(df_temp_adj)
        points_cols = col_info['points_cols']
        n_questions = len(points_cols)

        # adicionar informações meta no df
        df_temp_adj['Questoes_Prova'] = n_questions
        df_temp_adj['SourceFile'] = getattr(uf, 'name', str(uf))

        # popular mapa RA -> counts
        for ra, nome in zip(df_temp_adj['RA'], df_temp_adj['NOMEALUNO']):
            ra = str(ra).zfill(7)
            entry = {'file': getattr(uf, 'name', str(uf)), 'count': n_questions, 'nome': nome}
            ra_counts_map.setdefault(ra, []).append(entry)

        lista_dfs.append(df_temp_adj)

    if not lista_dfs:
        st.error("Nenhum arquivo válido carregado.")
        return

    # Verificar conflitos: RA presente em mais de um arquivo com counts diferentes
    conflitos = []
    for ra, infos in ra_counts_map.items():
        counts = sorted({info['count'] for info in infos})
        if len(counts) > 1:
            # conflito detectado
            conflito_entry = {
                'RA': ra,
                'Nome': infos[0].get('nome', ''),
                'Counts_Per_File': "; ".join([f"{i['file']} -> {i['count']}" for i in infos])
            }
            conflitos.append(conflito_entry)

    if conflitos:
        st.subheader("⚠️ Conflitos detectados: aluno presente em múltiplos arquivos com quantidades diferentes de questões")
        st.error("Você escolheu regra 4: isso é tratado como ERRO. Corrija os arquivos ou remova duplicatas.")
        df_conflitos = pd.DataFrame(conflitos)
        st.dataframe(df_conflitos)
        return

    # Se não há conflitos, concatenar todos os dfs
    df_all = pd.concat(lista_dfs, ignore_index=True, sort=False)

    # Construir df_questoes por RA (agrupar e pegar o valor de Questoes_Prova)
    df_questoes = df_all.groupby('RA')['Questoes_Prova'].first().reset_index().rename(columns={'Questoes_Prova': 'Questoes'})
    df_questoes['RA'] = df_questoes['RA'].astype(str).str.zfill(7)

    # Exibir tabela de controle de questões por aluno (questões detectadas, anuladas, ajustadas, possible points, diferença)
    st.subheader("📊 Controle de Quantidade de Questões por Aluno (baseado no ZipGrade)")
    qtd_anuladas = None  # será preenchido após input do usuário
    st.info("A coluna 'Questoes' abaixo foi obtida diretamente de cada arquivo ZipGrade (cada coluna '#X Points Earned' = 1 questão).")

    # Vamos exibir por agora: RA, NOMEALUNO (pegar do df_all), Questoes (detectadas), PossiblePoints_Atual (soma por RA)
    df_possible_actual = df_all.groupby('RA')['Possible Points'].sum().reset_index().rename(columns={'Possible Points': 'PossiblePoints_Atual'})
    # pegar nome do aluno (primeira ocorrência)
    df_nome = df_all.groupby('RA')['NOMEALUNO'].first().reset_index()
    df_qtd = pd.merge(df_questoes, df_nome, on='RA', how='left')
    df_qtd = pd.merge(df_qtd, df_possible_actual, on='RA', how='left')
    df_qtd['Questoes_Anuladas'] = 0  # placeholder, será atualizado depois
    df_qtd['Questoes_Apos_Anuladas'] = df_qtd['Questoes'] - df_qtd['Questoes_Anuladas']
    df_qtd['Diferenca'] = df_qtd['Questoes_Apos_Anuladas'] - df_qtd['PossiblePoints_Atual'].fillna(0)
    st.dataframe(df_qtd[['RA', 'NOMEALUNO', 'Questoes', 'Questoes_Anuladas', 'Questoes_Apos_Anuladas', 'PossiblePoints_Atual', 'Diferenca']].sort_values('RA'))

    # Parâmetros da prova e inputs do usuário
    prova = st.selectbox('Selecione o tipo de prova', ['Prova', 'Recuperação'])
    tipoetapa = 'N'
    codetapa = 3
    codprova = 1 if prova == "Prova" else 2

    questoes_anuladas_input = st.text_input("Informe questões anuladas (separadas por vírgula):", value="")
    questoes_anuladas = [int(q.strip()) for q in questoes_anuladas_input.split(",") if q.strip().isdigit()]
    # atualizar a tabela de controle com quantidade de anuladas
    qtd_anuladas = len(questoes_anuladas)
    df_qtd['Questoes_Anuladas'] = qtd_anuladas
    df_qtd['Questoes_Apos_Anuladas'] = df_qtd['Questoes'] - df_qtd['Questoes_Anuladas']
    df_qtd['Diferenca'] = df_qtd['Questoes_Apos_Anuladas'] - df_qtd['PossiblePoints_Atual'].fillna(0)
    st.subheader("📊 Controle (após informar questões anuladas)")
    st.dataframe(df_qtd[['RA', 'NOMEALUNO', 'Questoes', 'Questoes_Anuladas', 'Questoes_Apos_Anuladas', 'PossiblePoints_Atual', 'Diferenca']].sort_values('RA'))

    # Exibir alunos com NaNs e permitir ajustes (desconsiderar NaNs -> ajustar Possible Points)
    col_info_all = detectar_colunas_zipgrade(df_all)
    response_cols_all = col_info_all['response_cols']

    if response_cols_all:
        df_all['Nao_Respondidas'] = df_all[response_cols_all].isna().sum(axis=1)
    else:
        df_all['Nao_Respondidas'] = 0

    df_nulos = df_all[df_all['Nao_Respondidas'] > 0][['RA', 'NOMEALUNO', 'Nao_Respondidas']].copy()
    if not df_nulos.empty:
        st.subheader("Alunos com questões não respondidas (NaN)")
        st.warning(f"{len(df_nulos)} linhas com questões não respondidas.")
        st.dataframe(df_nulos.sort_values("Nao_Respondidas", ascending=False))

    selecionados_nomes = st.multiselect(
        "Selecionar alunos (por nome) para ajustar Possible Points (desconsiderar NaNs):",
        options=df_nulos['NOMEALUNO'].unique().tolist()
    )

    alunos_ajustar = {}
    if selecionados_nomes:
        df_sel = df_nulos[df_nulos['NOMEALUNO'].isin(selecionados_nomes)].copy()
        mapeamento = df_sel.groupby('RA')['Nao_Respondidas'].sum().to_dict()
        alunos_ajustar = {str(k).zfill(7): int(v) for k, v in mapeamento.items()}

    # Botão de calcular
    if st.button("Calcular Notas com Anulações"):
        with st.spinner("Processando..."):
            # filtrar base de alunos por curso/turma e excluir disciplinas (ainda usamos base para metadados)
            df_base_filtrada = df_base[
                (df_base['CURSO'] == curso_selecionado) &
                (df_base['TURMADISC'].isin(turma_selecionada)) &
                (~df_base['DISCIPLINA'].isin(disciplinas_excluidas))
            ].copy()

            # Chamar função principal de cálculo (df_all contém 'Questoes_Prova' por linha)
            df_final, df_discrepancias, df_zip_processado = aplicar_anuladas_e_calcular_notas(
                df_zip_all=df_all,
                df_alunos_base=df_base_filtrada,
                questoes_anuladas=questoes_anuladas,
                alunos_ajustar=alunos_ajustar,
                prova=prova,
                etapa="P3",
                codetapa=codetapa,
                codprova=codprova,
                tipoetapa=tipoetapa
            )

        # exibir discrepancias
        if not df_discrepancias.empty:
            st.subheader("Discrepâncias entre questões esperadas (Zip) e pontos do simulado")
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
