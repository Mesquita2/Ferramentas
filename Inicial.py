import os 
import streamlit as st
import pandas as pd
from auth import check_authentication, logout
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

st.set_page_config(page_title="Alteração de Dados", 
                   page_icon="", 
                   layout="wide")


# Verifica se o usuário está autenticado
if not check_authentication():
    st.stop()


# Estilo personalizado para os botões
st.markdown(
    """
    <style>
        .stButton>button {
            background-color: #5C2D91 !important;
            color: white !important;
            border-radius: 10px;
            padding: 10px 15px;
            font-size: 16px;
            border: none;
            transition: background-color 0.3s ease, transform 0.2s ease;
        }
        .stButton>button:hover {
            background-color: #48207E !important;
            transform: scale(1.05);
        }
    </style>
    """,
    unsafe_allow_html=True
)

COLUNAS_VISIVEIS = {
    "alunosxdisciplinas": ["CODTURMA", "CURSO", "ALUNO", "RA", "NOME_SOCIAL"],
    "disciplina": ["CODTURMA", "NOME", "IDMOODLE"],
    "rec": ["DISCIPLINA", "NOME"]
}

# Autenticação
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["google_service_account"],
    scopes=["https://www.googleapis.com/auth/drive.readonly"]
)
drive_service = build("drive", "v3", credentials=credentials)

# Lista de arquivos
NOME_ARQUIVOS = ["alunosxdisciplinas.xlsx", "disciplina.xlsx", "rec.xlsx"]

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
     
    return pd.DataFrame(df)

# Função para buscar e ler os arquivos
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
#
# Carregamento inicial se ainda não existir
if "dados" not in st.session_state:
    st.session_state["dados"] = {}
    for nome in NOME_ARQUIVOS:
        df = carregar_arquivo_drive(nome)
        if df is not None:
            chave = nome.replace(".xlsx", "")
            st.session_state["dados"][chave] = df
    st.success("Arquivos carregados do Drive.")


# Interface para visualização e substituição
st.title("Arquivos carregados")

df_alunos = st.session_state["dados"]["alunosxdisciplinas"]
df_teste = limpeza_alunos_disciplinas(df_alunos)
st.session_state["dados"]["alunosxdisciplinas"] = df_teste

for chave, df in st.session_state["dados"].items():
    st.subheader(f"{chave}")

    # Aplica filtro de colunas se estiver definido
    colunas = COLUNAS_VISIVEIS.get(chave)
    if colunas:
        df_exibido = df.loc[:, df.columns.intersection(colunas)]
    else:
        df_exibido = df

    st.dataframe(df_exibido)

    uploaded_file = st.file_uploader(
        f"Substituir {chave}.xlsx",
        type=["xlsx"],
        key=chave
    )
    if uploaded_file:
        novo_df = pd.read_excel(uploaded_file)
        st.session_state["dados"][chave] = novo_df
        st.success(f"Arquivo {chave}.xlsx substituído com sucesso.")
        
        # Aplica o mesmo filtro após substituição
        novo_exibido = novo_df.loc[:, novo_df.columns.intersection(colunas)] if colunas else novo_df
        st.dataframe(novo_exibido)
         