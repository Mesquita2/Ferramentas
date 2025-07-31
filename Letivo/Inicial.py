import os 
import streamlit as st
import pandas as pd
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

def carregar():
    st.title("Início")

    # Autenticação e conexão com o Drive
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["google_service_account"],
        scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    drive_service = build("drive", "v3", credentials=credentials)

    NOME_ARQUIVOS = ["alunosxdisciplinas.xlsx", "disciplina.xlsx", "rec.xlsx", "rec_simulado.xlsx"]

    def carregar_arquivo_drive(nome_arquivo):
        response = drive_service.files().list(
            q=f"name = '{nome_arquivo}' and trashed = false",
            spaces="drive",
            fields="files(id, name, mimeType)",
        ).execute()

        files = response.get("files", [])
        if not files:
            st.warning(f"Arquivo '{nome_arquivo}' não encontrado.")
            return None

        file = files[0]
        file_id = file["id"]
        mime_type = file["mimeType"]
        fh = io.BytesIO()

        if mime_type == "application/vnd.google-apps.spreadsheet":
            request = drive_service.files().export_media(
                fileId=file_id,
                mimeType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            request = drive_service.files().get_media(fileId=file_id)

        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

        fh.seek(0)
        return pd.read_excel(fh)

    def limpeza_alunos_disciplinas(df):
        if 'NOME_SOCIAL' in df.columns:
            df['NOMEALUNO'] = df['NOME_SOCIAL'].where(
                df['NOME_SOCIAL'].notna() & (df['NOME_SOCIAL'] != ''),
                df['NOMEALUNO']
            )
            df.drop(columns=['NOME_SOCIAL'], inplace=True) 

        df.rename(columns={'NOMEDISCIPLINA': 'DISCIPLINA',
                           'NOMECURSO': 'CURSO',
                           'NOMEALUNO': 'ALUNO'}, inplace=True)
        df = df[df['NOMESTATUS'] != 'Cancelamento']
        df = df[df['NOMESTATUS'] != 'Aproveitamento de Estudo']
        df = df.assign(RA=df['RA'].apply(str).str.zfill(7))
        return df

    # Carregar dados apenas uma vez
    if "dados" not in st.session_state:
        st.session_state["dados"] = {}
        with st.spinner("Carregando arquivos do Drive, por favor aguarde..."):
            # — inicialize drive_service aqui —
            for nome in NOME_ARQUIVOS:
                df = carregar_arquivo_drive(nome)
                if df is not None:
                    chave = nome.replace(".xlsx", "")
                    st.session_state["dados"][chave] = df

        st.success("Arquivos carregados com sucesso!")
        st.rerun()

    # Aplicar limpeza nos dados de alunos
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
                "rec": ["DISCIPLINA", "NOME"]
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
