from matplotlib.font_manager import json_dump
import streamlit as st
import pandas as pd
from carregamento import carregar_drive, limpeza_alunos_disciplinas, carregar_totvs
import datetime
from datetime import date, datetime


def carregar():
    st.title("Início")
    
    carregar_drive()
    
    agora = datetime.now()
    ano = agora.year
    semestre = 1 if agora.month <= 6 else 2
    opcoes = [f"{ano}.{semestre}", 
              f"{ano}.{1 if semestre == 2 else 2}",
            ]
    opcoes.append("2025.4")

    # Selectbox para usuário escolher
    periodo = st.selectbox("Selecione o período letivo:", opcoes, index=0)
    st.write(f"Período escolhido: {periodo}")

    # Verifica se o período mudou ou se ainda não foi carregado
    if (
        "periodo_carregado" not in st.session_state 
        or st.session_state["periodo_carregado"] != periodo
    ):
        st.info("Carregando dados do TOTVS...")

        # === 1. Buscar dados de alunos x disciplinas ===
        arquivo = carregar_totvs("caminho_periodo_letivo", periodo)

        if isinstance(arquivo, dict):
            lista = list(arquivo.values())
        else:
            lista = arquivo  # caso já seja lista

        df = pd.DataFrame(lista)
        if df is None or df.empty:
            st.warning("Nenhum dado retornado do TOTVS para alunos x disciplinas.")
        else:
            df_limpo = limpeza_alunos_disciplinas(df)
            st.session_state["dados"]["alunosxdisciplinas"] = df_limpo
            st.success("Dados de alunos x disciplinas carregados.")

        # === 2. Buscar dados de professores ===
        professores = carregar_totvs("caminho_periodo_professores", periodo)

        if isinstance(professores, dict):
            lista_prof = list(professores.values())
        else:
            lista_prof = professores

        df_prof = pd.DataFrame(lista_prof)
        if df_prof is None or df_prof.empty:
            st.warning("Nenhum dado retornado do TOTVS para professores.")
        else:
            st.session_state["dados"]["professores"] = df_prof
            st.success("Dados de professores carregados.")
            
        # ======================
        alunos_dados = carregar_totvs("caminho_alunos_dados", periodo)

        if isinstance(alunos_dados, dict):
            alunos_lista = list(alunos_dados.values())
        else:
            alunos_lista = alunos_dados

        df_alunos_dados = pd.DataFrame(alunos_lista)
        if df_alunos_dados is None or df_alunos_dados.empty:
            st.warning("Nenhum dado retornado do TOTVS para alunos.")
        else:
            st.session_state["dados"]["alunosxdisciplinas_email"] = df_alunos_dados
            st.success("Dados de alunos carregados.")

        # === Atualiza o período salvo ===
        st.session_state["periodo_carregado"] = periodo

    else:
        st.info("Usando dados já carregados do período selecionado.")


    # Recupera o DataFrame do estado da sessão
    df_alunos = st.session_state["dados"].get("alunosxdisciplinas", pd.DataFrame())
    df_alunos = limpeza_alunos_disciplinas(df_alunos)

    # Criar abas
    tab1, tab2 = st.tabs(["Visualizar dados", "Substituir arquivos"])

    with tab1:
        
        for chave, df in st.session_state["dados"].items():
            st.subheader(f"{chave}")
            colunas = {
                "alunosxdisciplinas": ["CODTURMA", "CURSO", "ALUNO", "NOME_SOCIAL", "RA"],
                "professores": ["CODPROF","PROFESSOR","CURSO", "DISCIPLINA"],
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
