import streamlit as st
import pandas as pd
from carregamento import carregar_drive, limpeza_alunos_disciplinas


def carregar():
    st.title("Início")
    
    carregar_drive()

    df_alunos = st.session_state["dados"]["alunosxdisciplinas"]
    df_limpo = limpeza_alunos_disciplinas(df_alunos)
    st.session_state["dados"]["alunosxdisciplinas"] = df_limpo

    # Criar abas
    tab1, tab2 = st.tabs(["Visualizar dados", "Substituir arquivos"])

    with tab1:
        for chave, df in st.session_state["dados"].items():
            st.subheader(f"{chave}")
            colunas = {
                "alunosxdisciplinas": ["CODTURMA", "CURSO", "ALUNO", "RA"],
                "disciplina": ["CODTURMA", "NOME", "IDMOODLE"],
                "rec": ["DISCIPLINA", "NOME"],
                "rec_simulado":["DISCIPLINA", "NOME"]
            }.get(chave)
            df_exibido = df.loc[:, df.columns.intersection(colunas)] if colunas else df
            st.dataframe(df_exibido, use_container_width=True)

    with tab2:
        for chave in st.session_state["dados"].keys():
            st.subheader(f"Substituir {chave}.xlsx")
            uploaded_file = st.file_uploader(
                f"Novo arquivo para {chave}",
                type=["xlsx"],
                key=chave
            )
            if uploaded_file:
                novo_df = pd.read_excel(uploaded_file)
                st.session_state["dados"][chave] = novo_df
                st.success(f"Arquivo {chave}.xlsx substituído com sucesso.")
                st.dataframe(novo_df, use_container_width=True)
