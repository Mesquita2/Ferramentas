import streamlit as st
import pandas as pd
import io
import os

from dotenv import load_dotenv

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

load_dotenv()

def gerar_excel(df):
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="resultado")

    output.seek(0)

    return output


def carregar_planilha_fotos(drive_service):

    sheet_id = st.secrets["caminho_planilha_fotos"]["PLANILHA_FOTOS"]

    request = drive_service.files().export_media(
        fileId=sheet_id,
        mimeType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)

    done = False
    while not done:
        _, done = downloader.next_chunk()

    fh.seek(0)

    df = pd.read_excel(fh)

    return df

def carregar():
    

    df_totvs_email = st.session_state["dados"].get(
        "alunosxdisciplinas_email", pd.DataFrame()
    ).copy()

    df_totvs_email = df_totvs_email.drop_duplicates(subset=["EMAILALUNO"])

    if df_totvs_email.empty:
        st.warning("Dados de alunos x disciplinas não encontrados.")
        return

    st.title("Validação de Fotos dos Alunos")

    # autenticação drive
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["google_service_account"],
        scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )

    drive_service = build("drive", "v3", credentials=credentials)

    # 🔹 carregar planilha usando ID do .env
    df_fotos = carregar_planilha_fotos(drive_service)

    # padronizar emails
    df_fotos["Email institucional"] = df_fotos["Email institucional"].str.strip().str.lower()
    df_totvs_email["EMAILALUNO"] = df_totvs_email["EMAILALUNO"].str.strip().str.lower()

    # merge mantendo todos da planilha de fotos
    df_final = df_fotos.merge(
        df_totvs_email[["EMAILALUNO", "RA", "NOMEALUNO"]],
        left_on="Email institucional",
        right_on="EMAILALUNO",
        how="left",
        indicator=True
    )

    st.dataframe(df_final)

    excel_file = gerar_excel(df_final)

    st.download_button(
        label="Baixar resultado em Excel",
        data=excel_file,
        file_name="validacao_fotos_alunos.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )