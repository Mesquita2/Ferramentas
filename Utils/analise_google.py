import streamlit as st
import pandas as pd
from datetime import datetime

# ==============================
# PROJETO SIMPLES – COMPARADOR
# ==============================

# USA SEU JEITO DE CARREGAR DADOS
from carregamento import carregar_drive, carregar_totvs, limpeza_alunos_disciplinas


# ------------------------------
# FUNÇÃO PRINCIPAL
# ------------------------------

def carregar():
    st.title("Comparador de Membros (CSV) x Alunos por Curso")

    # Garante estrutura no session_state
    if "dados" not in st.session_state:
        st.session_state["dados"] = {}

    # ==============================
    #  CARREGAR DADOS (SEU PADRÃO)
    # ==============================
    carregar_drive()

    agora = datetime.now()
    ano = agora.year
    semestre = 1 if agora.month <= 6 else 2

    opcoes = [f"{ano}.{semestre}", f"{ano}.{1 if semestre == 2 else 2}"]
    periodo = st.selectbox("Selecione o período letivo:", opcoes, index=0)

    if (
        "periodo_carregado" not in st.session_state
        or st.session_state["periodo_carregado"] != periodo
    ):
        st.info("Carregando dados do TOTVS...")

        arquivo = carregar_totvs("caminho_alunos_dados", periodo)

        if isinstance(arquivo, dict):
            lista = list(arquivo.values())
        else:
            lista = arquivo

        df = pd.DataFrame(lista)

        if df is None or df.empty:
            st.warning("Nenhum dado retornado do TOTVS.")
            return

        df_limpo = limpeza_alunos_disciplinas(df)
        st.session_state["dados"]["alunosxdisciplinas_email"] = df_limpo
        st.session_state["periodo_carregado"] = periodo
        st.success("Dados carregados.")

    # ==============================
    #  DATAFRAME DE ALUNOS
    # ==============================
    df_alunos = st.session_state["dados"].get("alunosxdisciplinas_email", pd.DataFrame()).copy()

    if df_alunos.empty:
        st.warning("Sem dados de alunos carregados.")
        return

    # Padronização
    df_alunos.columns = df_alunos.columns.str.strip().str.upper()
    df_alunos["CURSO"] = df_alunos["CURSO"].astype(str).str.strip().str.upper()
    df_alunos["EMAILALUNO"] = df_alunos["EMAILALUNO"].astype(str).str.strip().str.lower()

    # ==============================
    #  UPLOAD DO CSV
    # ==============================
    st.divider()
    st.subheader("Envie o CSV de membros (export do Google)")

    arquivo_csv = st.file_uploader("Arquivo CSV", type="csv")

    if arquivo_csv is None:
        st.info("Envie o CSV para comparar.")
        return

    df_csv = pd.read_csv(arquivo_csv)

    # Ajusta nomes padrão do CSV
    df_csv.columns = df_csv.columns.str.strip()

    if "Member Email" not in df_csv.columns:
        st.error("O CSV precisa ter a coluna 'Member Email'")
        st.write(df_csv.columns)
        return

    df_csv["Member Email"] = df_csv["Member Email"].astype(str).str.strip().str.lower()

    # ==============================
    # SELECT DE CURSO
    # ==============================
    curso_escolhido = st.selectbox(
        "Selecione o curso",
        sorted(df_alunos["CURSO"].unique())
    )

    df_curso = df_alunos[df_alunos["CURSO"] == curso_escolhido].drop_duplicates("RA")

    # ==============================
    # COMPARAÇÃO
    # ==============================
    emails_totvs = set(df_curso["EMAILALUNO"])
    emails_csv = set(df_csv["Member Email"])

    # No CSV mas não no curso
    so_no_csv = df_csv[~df_csv["Member Email"].isin(emails_totvs)][["Member Name", "Member Email"]]

    # No curso mas não no CSV
    so_no_totvs = df_curso[~df_curso["EMAILALUNO"].isin(emails_csv)][["ALUNO", "EMAILALUNO"]]

    
    st.divider()
    st.subheader(f"Resultados — {curso_escolhido}")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### No CSV mas NÃO matriculados no curso")
        st.dataframe(so_no_csv, use_container_width=True)
        st.metric("Total", len(so_no_csv))

    with col2:
        st.markdown("###  Matriculados no curso mas FORA do CSV")
        st.dataframe(so_no_totvs, use_container_width=True)
        st.metric("Total", len(so_no_totvs))


        
        if not so_no_totvs.empty:
            # CSV no template padrão do Google Groups
            df_export = pd.DataFrame({
                "Group Email [Required]": "substituir@somosicev.com",
                "Member Email": so_no_totvs["EMAILALUNO"].values,
                "Member Type": "USER",
                "Member Role": "MEMBER",
            })


            csv_bytes = df_export.to_csv(index=False).encode("utf-8")


            st.download_button(
            " Baixar CSV pronto para importar no Google",
            data=csv_bytes,
            file_name=f"membros_para_adicionar_{curso_escolhido}.csv",
            mime="text/csv"
            )