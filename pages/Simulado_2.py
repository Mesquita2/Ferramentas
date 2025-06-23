import io
import streamlit as st
from auth import check_authentication
import pandas as pd
import numpy as np

st.set_page_config(page_title="Limpeza Simulado e REC Simulado", layout="wide")

if not check_authentication():
    st.stop()

# Carregar os dados dos alunos
df_alunos = st.session_state["dados"].get("alunosxdisciplinas")
df_base = df_alunos.copy()

padrao_remover = r'(?:Projeto de Extensão|Seminários|Liga dos Campeões|Estágio|TCC|Trabalho de Conclusão de Curso)'
df_base = df_base[~df_base['DISCIPLINA'].str.contains(padrao_remover, case=False, na=False)].reset_index(drop=True)

# Renomear colunas
df_base.rename(columns={
    'NOMEDISCIPLINA': 'DISCIPLINA',
    'NOMECURSO': 'CURSO',
    'NOMEALUNO': 'ALUNO'
}, inplace=True)

@st.cache_data
def carregar_dados(arquivo):
    try:
        return pd.read_excel(arquivo)
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo: {e}")
        return pd.DataFrame()

def calcula_qtd_questoes(df):
    df = df.copy()
    df['Questoes'] = 0

    # Mapas de crédito para questões
    credito_to_questoes = {4: 12, 2: 6}

    # ADMINISTRAÇÃO
    mask_adm = df['CURSO'] == 'Administração de Empresas'
    df.loc[mask_adm, 'Questoes'] = df.loc[mask_adm, 'NUMCREDITOSCOB'].map(credito_to_questoes).fillna(0).astype(int)

    # DIREITO
    mask_dir = df['CURSO'] == 'Direito'
    df.loc[mask_dir, 'Questoes'] = df.loc[mask_dir, 'NUMCREDITOSCOB'].map(credito_to_questoes).fillna(0).astype(int)

    # ENGENHARIA DE SOFTWARE
    mask_eng = df['CURSO'] == 'Engenharia de Software'
    df_eng = df[mask_eng].copy()

    # Tratar TURMADISC: remover NaNs e padronizar
    df_eng['TURMADISC'] = df_eng['TURMADISC'].fillna('').astype(str).str.upper().str.strip()

    # Verificar se cada aluno de engenharia tem '037C'
    df_eng['Tem_037C'] = df_eng['TURMADISC'].apply(lambda x: '037C' in x)

    # Agrupar por aluno para ver se tem 037C em qualquer disciplina
    questoes_eng = (
        df_eng.groupby(['ALUNO', 'RA'])['Tem_037C']
        .any()
        .reset_index()
    )
    questoes_eng['Questoes'] = questoes_eng['Tem_037C'].apply(lambda x: 30 if x else 60)
    questoes_eng.drop(columns='Tem_037C', inplace=True)

    # ADM/DIR - somar por aluno
    df_adm_dir = df.loc[~mask_eng].groupby(['ALUNO', 'RA'])['Questoes'].sum().reset_index()

    # Juntar tudo
    df_final = pd.concat([df_adm_dir, questoes_eng], ignore_index=True)

    # Agrupar final (pode ter aluno que está em ADM + ENG)
    df_final = df_final.groupby(['ALUNO', 'RA'], as_index=False)['Questoes'].sum()
    df_final['RA'] = df_final['RA'].astype(str).str.zfill(7)

    return df_final


def ajustes_dataframe(df):
    df['Student ID'] = df['Student ID'].astype(str).str.zfill(7).copy()
    df['ALUNO'] = df['Student First Name'].fillna('') + ' ' + df['Student Last Name'].fillna('')
    df['ALUNO'] = df['ALUNO'].str.strip()

    # Filtrar apenas linhas válidas
    df = df[(df['Student ID'] != '0') & (df['ALUNO'] != '')].copy()
    df['Student ID'] = df['Student ID'].astype(str).str.zfill(7)
    df['ALUNO'] = df['Student First Name'].fillna('') + ' ' + df['Student Last Name'].fillna('')
    df['ALUNO'] = df['ALUNO'].str.strip()
    df = df[(df['Student ID'] != '0') & (df['ALUNO'] != '')]
    df.rename(columns={'Student ID': 'RA', 'ALUNO': 'NOMEALUNO'}, inplace=True)


    # Renomear sem afetar outras colunas
    df.rename(columns={'Student ID': 'RA', 'ALUNO': 'NOMEALUNO'}, inplace=True)

    return df


def limpar_dados(df, prova, etapa, codetapa, codprova, tipoetapa, questoes_anuladas, disciplinas_excluidas, turma_selecionada):
    df_base_local = df_alunos.copy()
    padrao_remover = r'(?:Projeto de Extensão|Seminários|Liga dos Campeões|Estágio|TCC|Trabalho de Conclusão de Curso)'
    df_base_local = df_base[~df_base['DISCIPLINA'].str.contains(padrao_remover, case=False, na=False)].reset_index(drop=True)
    df_base_local.rename(columns={
        'NOMEDISCIPLINA': 'DISCIPLINA',
        'NOMECURSO': 'CURSO',
        'NOMEALUNO': 'ALUNO'
    }, inplace=True)

    # Aplicar exclusão de disciplinas
    df_base_local = df_base_local[~df_base_local['DISCIPLINA'].isin(disciplinas_excluidas)]

    # Ajustar formato do RA para padronizar e filtrar só alunos do simulado
    df_base_local['RA'] = df_base_local['RA'].astype(str).str.zfill(7)
    r_as_simulado = df['RA'].astype(str).str.zfill(7).unique()
    df_base_local = df_base_local[df_base_local['RA'].isin(r_as_simulado)]

    # Calcular questões só para alunos do simulado
    df_questoes = calcula_qtd_questoes(df_base_local)

    df['RA'] = df['RA'].astype(str).str.zfill(7)
    df_simulado_pontos = df.groupby('RA')['Possible Points'].sum().reset_index()
    df_simulado_pontos.rename(columns={'Possible Points': 'PontosSimulado'}, inplace=True)

    # Garantir RA formatado antes do merge
    df_questoes['RA'] = df_questoes['RA'].astype(str).str.zfill(7)
    df_simulado_pontos['RA'] = df_simulado_pontos['RA'].astype(str).str.zfill(7)

    df_validacao = pd.merge(df_questoes, df_simulado_pontos, on='RA', how='left')
    df_validacao['DiferencaQuestoes'] = df_validacao['Questoes'] - df_validacao['PontosSimulado'].fillna(0)

    df_discrepancias = df_validacao[df_validacao['DiferencaQuestoes'] != 0]

    if not df_discrepancias.empty:
        st.subheader("Alunos com Discrepâncias entre Questões Esperadas e Pontos do Simulado")
        st.warning("Ajuste manual necessário.")
        st.dataframe(df_discrepancias[['ALUNO', 'RA', 'Questoes', 'PontosSimulado', 'DiferencaQuestoes']])

        st.subheader("Correção Manual de Pontos no Simulado")
        with st.form("form_correcoes"):
            novas_pontuacoes = {}

            for _, row in df_discrepancias.iterrows():
                ra = row['RA']
                aluno = row['ALUNO']
                pontos_atual = row['PontosSimulado'] if pd.notna(row['PontosSimulado']) else 0
                esperado = row['Questoes']

                try:
                    pontos_atual_float = float(pontos_atual)
                except:
                    pontos_atual_float = 0.0

                esperado_float = float(esperado) if pd.notnull(esperado) else 0.0
                valor_inicial = min(pontos_atual_float, esperado_float)

                novo_valor = st.number_input(
                    f"{aluno} (RA: {ra}) - Pontos atuais: {pontos_atual} | Esperado: {esperado}",
                    min_value=0.0,
                    max_value=esperado_float,
                    value=valor_inicial,
                    step=0.1,
                    key=f"correcao_{ra}"
                )

                novas_pontuacoes[ra] = novo_valor

            submitted = st.form_submit_button("Aplicar Correções")
            if submitted:
                for ra, novo_ponto in novas_pontuacoes.items():
                    df.loc[df['RA'] == ra, 'Possible Points'] = novo_ponto
                st.success("Correções aplicadas. Recalcule as notas.")

    df['Earned Points Original'] = df['Earned Points'].fillna(0)
    ids = df['RA'].astype(str).str.zfill(7)
    bonus_total = pd.Series(0, index=ids.unique())

    for q in questoes_anuladas:
        coluna = f"#{q} Points Earned"
        if coluna in df.columns:
            ganhos = (df[coluna].fillna(0) == 0).astype(int)
            bonus = pd.Series(ganhos.values, index=ids).groupby(level=0).sum()
            bonus_total = bonus_total.add(bonus, fill_value=0)

    df['Bonus Anuladas'] = ids.map(bonus_total).fillna(0)
    df['Earned Points Final'] = df['Earned Points Original'] + df['Bonus Anuladas']
    df['NOTAS'] = np.minimum((df['Earned Points Final'] * 1.25) / df['Possible Points'].replace(0, np.nan), 1).fillna(0) * 10

    st.subheader("Dados Originais com Notas")
    st.dataframe(df)

    df_base_local['RA'] = df_base_local['RA'].astype(str).str.zfill(7)
    df['RA'] = df['RA'].astype(str).str.zfill(7)

    df_final = pd.merge(df_base_local, df[['RA', 'NOTAS']], on='RA', how='left')
    df_final['CODETAPA'] = codetapa
    df_final['CODPROVA'] = codprova
    df_final['TIPOETAPA'] = tipoetapa
    df_final['PROVA'] = prova
    df_final['ETAPA'] = etapa

    colunas = ['CODCOLIGADA', 'CURSO', 'TURMADISC', 'IDTURMADISC', 'DISCIPLINA', 'RA', 'ALUNO', 'ETAPA', 'PROVA', 'TIPOETAPA', 'CODETAPA', 'CODPROVA', 'NOTAS']
    df_final = df_final[colunas]

    return df_final


# Interface Streamlit
st.title("Tratamento de Notas Simulado e REC Simulado")

cursos_disponiveis = sorted(df_base['CURSO'].dropna().unique())

curso_selecionado = st.selectbox("Selecione o curso para filtrar as disciplinas:", index=None, options=cursos_disponiveis)


if curso_selecionado:
    turmas_disponiveis = sorted(df_base[df_base['CURSO'] == curso_selecionado]['TURMADISC'].dropna().unique())
    turma_selecionada = st.multiselect("Selecione a Turma:", options=turmas_disponiveis)

    if turma_selecionada:
        disciplinas_disponiveis = sorted(
            df_base[
                (df_base['CURSO'] == curso_selecionado) &
                (df_base['TURMADISC'].isin(turma_selecionada))
            ]['DISCIPLINA'].dropna().unique()
        )

        disciplinas_excluidas = st.multiselect("Disciplinas que NÃO são aplicadas no Simulado:", options=disciplinas_disponiveis, default=[])
        uploaded_file = st.file_uploader("Envie o arquivo de notas (Excel)", type=["xlsx"])

        if uploaded_file:
            df_original = carregar_dados(uploaded_file)
            st.subheader("Dados Originais")
            st.dataframe(df_original)
            df_ajustado_zipgrade = ajustes_dataframe(df_original)

            etapa = "P3"
            prova = st.selectbox('Selecione o tipo de prova', ['Prova', 'Recuperação'])
            tipoetapa = 'N'
            codetapa = 3
            codprova = 1 if prova == "Prova" else 2

            questoes_anuladas_input = st.text_input("Informe questões anuladas (separadas por vírgula):", value="")
            questoes_anuladas = [int(q.strip()) for q in questoes_anuladas_input.split(",") if q.strip().isdigit()]

            if st.button("Calcular Notas com Anulações"):
                df_limpo = limpar_dados(df_ajustado_zipgrade, prova, etapa, codetapa, codprova, tipoetapa, questoes_anuladas, disciplinas_excluidas, turma_selecionada)
                
                df_limpo['NOTAS'] = pd.to_numeric(df_limpo['NOTAS'], errors='coerce').round(2)
                df_limpo['NOTAS'] = df_limpo['NOTAS'].apply(lambda x: f"{x:.2f}".replace('.', ','))

                st.subheader("Notas Finais")
                st.dataframe(df_limpo)

                df_limpo['RA'] = df_limpo['RA'].astype(str).str.zfill(7)

                output = io.BytesIO()
                df_limpo.to_csv(output, index=False, sep=';', encoding='utf-8', header=False)
                output.seek(0)

                classe = df_limpo['TURMADISC'].iloc[0] if not df_limpo.empty else "sem_classe"

                st.download_button(
                    label="⬇ Baixar Notas Tratadas (TXT)",
                    data=output,
                    file_name=f"{classe}_{prova}.txt",
                    mime="text/plain"
                )
