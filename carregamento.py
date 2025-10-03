import io
import pandas as pd
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

NOME_ARQUIVOS = ["alunosxdisciplinas.xlsx", "disciplina.xlsx", "rec.xlsx", "rec_simulado.xlsx", "dashnotas.xlsx", "alunosxdisciplinas_geral.xlsx"]

def carregar_arquivo_drive(drive_service, nome_arquivo):
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

def carregar_drive():
    if "dados" not in st.session_state:
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["google_service_account"],
            scopes=["https://www.googleapis.com/auth/drive.readonly"]
        )
        drive_service = build("drive", "v3", credentials=credentials)

        st.session_state["dados"] = {}
        with st.spinner("Carregando arquivos do Drive, por favor aguarde..."):
            for nome in NOME_ARQUIVOS:
                df = carregar_arquivo_drive(drive_service, nome)
                if df is not None:
                    chave = nome.replace(".xlsx", "")
                    st.session_state["dados"][chave] = df
        st.success("Arquivos carregados com sucesso!")
        st.rerun()

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

def carregar_totvs(perletivo):
    import streamlit as st
    import requests
    from requests.auth import HTTPBasicAuth

    st.title("Exemplo de Request com Basic Auth")

    # Credenciais (poderiam vir do st.secrets)
    usuario = st.secrets["basic_auth"]["usuario"]  
    senha = st.secrets["basic_auth"]["senha"]
                
    url = st.secrets["caminho_periodo_letivo"]["link"] + str(perletivo)
    response = requests.get(url, auth=HTTPBasicAuth(usuario, senha))

    if response.status_code == 200:
        st.success("OK")
        #st.json(response.json())
    else:
        st.error(f"Erro: {response.status_code}")
        st.text(response.text)
            
    response = response.json()
    return response