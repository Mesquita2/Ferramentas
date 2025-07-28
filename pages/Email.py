import streamlit as st
import pandas as pd
import base64
import pickle
import os
import io 
import time
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
from googleapiclient.discovery import build
import pickle
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import base64
from auth import check_authentication


token_b64 = st.secrets["gmail_token"]["token_b64"]
pasta_raiz = st.secrets["drive_pasta"]["drive_provas"]

if not check_authentication():
    st.stop()

with open("token_gmail.pkl", "wb") as token_file:
    token_file.write(base64.b64decode(token_b64))

with open("token_gmail.pkl", "rb") as token:
    creds = pickle.load(token)

drive_service = build("drive", "v3", credentials=creds)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/drive.file", 
    "https://www.googleapis.com/auth/drive.metadata",  
]

TOKEN_PATH = "token_gmail.pkl"

def carregar_credenciais():
    creds = None
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, "rb") as token_file:
            creds = pickle.load(token_file)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    # Se token inválido ou não existe, pede upload
    if not creds or not creds.valid:
        st.warning("Token inválido ou expirado. Faça upload do arquivo token_gmail.pkl gerado localmente.")
        uploaded_token = st.file_uploader("Upload do token_gmail.pkl", type=["pkl"])
        if uploaded_token is not None:
            with open(TOKEN_PATH, "wb") as f:
                f.write(uploaded_token.getbuffer())
            st.success("Token salvo. Por favor, recarregue a página para continuar.")
            st.stop()
        else:
            st.stop()

    return creds

@st.cache_resource(show_spinner=False)
def criar_servico_gmail():
    creds = carregar_credenciais()
    return build("gmail", "v1", credentials=creds)

# --- Início do seu código ---
if "dados" not in st.session_state:
    st.session_state["dados"] = {"alunosxdisciplinas": pd.DataFrame()}

df_alunos = st.session_state["dados"].get("alunosxdisciplinas", pd.DataFrame())
df_base = df_alunos.copy()

def saudacao():
    h = datetime.now().hour
    return "Bom dia" if h<12 else "Boa tarde" if h<18 else "Boa noite"

def semestres(dt):
    return f"{dt.year}.01" if dt.month<=6 else f"{dt.year}.02"

def create_assunto(curso, disciplina, quantidade, tipo, tipo_prova, data_aplicar, turma):
    assunto = f'Prova iCEV {disciplina} - {tipo} - {quantidade} cópias, Turma: {turma}'
    msg = (
        f"{saudacao()}.\n\n"
        "Solicitamos a impressão de:\n\n"
        f"Tipo: {tipo_prova}\n"
        f"Curso/Turma: {curso} {semestres(data_aplicar)} {turma}\n"
        f"Disciplina: {disciplina}\n"
        f"Quantidade: {quantidade} cópias\n\n"
        f"Data: {data_aplicar.strftime('%d/%m/%Y')}"
    )
    return assunto, msg

def destinatarios(curso):
    base = list(st.secrets["emails"].values())
    cord = st.secrets["email_cord"]
    m = {"Engenharia de Software": cord.get("eng"),
         "Direito": cord.get("dir"),
         "Administração de Empresas": cord.get("adm")}
    e = m.get(curso.strip())
    return base + ([e] if e else [])

def enviar_email_gmail_api(remetente, destinatarios, assunto, mensagem, arquivo=None, tentativas=3, espera=2):
    service = criar_servico_gmail()

    for tentativa in range(1, tentativas + 1):
        try:
            msg = MIMEMultipart()
            msg["From"] = remetente
            msg["To"] = ", ".join(destinatarios)
            msg["Subject"] = assunto
            msg.attach(MIMEText(mensagem, "plain"))
            if arquivo:
                arquivo.seek(0)
                part = MIMEApplication(arquivo.read(), Name=arquivo.name)
                part["Content-Disposition"] = f'attachment; filename="{arquivo.name}"'
                msg.attach(part)
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            service.users().messages().send(userId="me", body={"raw": raw}).execute()
            return True  
        except Exception as e:
            print(f"Tentativa {tentativa} falhou: {e}")
            if tentativa < tentativas:
                time.sleep(espera)
            else:
                return False 
    
def upload_para_drive(arquivo, nome_arquivo, pasta_destino_id):
    # Autenticando com a Service Account
    creds = service_account.Credentials.from_service_account_info(
        st.secrets["google_service_account"],
        scopes=["https://www.googleapis.com/auth/drive.file"]
    )

    # Conectando com a API do Drive
    service = build("drive", "v3", credentials=creds)

    # Prepara o arquivo para upload
    media = MediaIoBaseUpload(io.BytesIO(arquivo.read()), mimetype=arquivo.type)

    # Define metadados do arquivo
    file_metadata = {
        "name": nome_arquivo,
        "parents": [pasta_destino_id]
    }

    # Faz o upload
    uploaded_file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, name"
    ).execute()

    return uploaded_file["id"], uploaded_file["name"]

def encontrar_ou_criar_pasta(nome, id_pasta_mae):
    """
    Verifica se a pasta já existe dentro da pasta mãe. Se não existir, cria.
    Retorna o ID da pasta.
    """
    query = f"'{id_pasta_mae}' in parents and name = '{nome}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    resultados = drive_service.files().list(q=query, fields="files(id, name)").execute()
    arquivos = resultados.get("files", [])

    if arquivos:
        return arquivos[0]["id"]
    else:
        # Cria a pasta
        metadata = {
            "name": nome,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [id_pasta_mae],
        }
        pasta = drive_service.files().create(body=metadata, fields="id").execute()
        return pasta["id"]

def salvar_arquivo_em_pasta(uploaded_file, nome_arquivo, curso, turma, pasta_raiz_id):
    # Etapa 1: Criar ou obter pasta do curso
    pasta_curso_id = encontrar_ou_criar_pasta(curso, pasta_raiz_id)

    # Etapa 2: Criar ou obter pasta da turma
    pasta_turma_id = encontrar_ou_criar_pasta(turma, pasta_curso_id)

    # Etapa 3: Enviar o arquivo
    media = MediaIoBaseUpload(uploaded_file, mimetype=uploaded_file.type)

    metadata = {
        "name": nome_arquivo,
        "parents": [pasta_turma_id],
    }

    arquivo = drive_service.files().create(
        body=metadata,
        media_body=media,
        fields="id, name"
    ).execute()

    return arquivo["id"], arquivo["name"]

# --- Interface Streamlit ---
st.title("Envio de Provas por E-mail (Gmail API)")

remetente = st.secrets["email_sis"]["sistema"]

cursos = sorted(df_base['CURSO'].dropna().unique())
curso = st.selectbox("Curso", cursos)
if curso: 
    disciplinas = sorted(df_base[df_base["CURSO"]==curso]["DISCIPLINA"].dropna().unique())
    disciplina = st.selectbox("Disciplina", disciplinas)
if disciplina:
    turmas = sorted(df_base[(df_base["DISCIPLINA"]==disciplina)]["TURMADISC"].dropna().unique())
    turma = st.selectbox("Turma", turmas)

quantidade = df_base[(df_base["DISCIPLINA"]==disciplina)&(df_base["TURMADISC"]==turma)]['ALUNO'].count() + 5
st.markdown(f"**Quantidade de cópias:** {quantidade}")

data_aplicar = st.date_input("Data da prova")
tipo = st.selectbox("Tipo", ["Prova","Recuperação"])
tipo_prova = st.selectbox("Nº Prova", ["1","2"])

assunto, mensagem = create_assunto(curso, disciplina, quantidade, tipo, tipo_prova, data_aplicar, turma)
dest_list = destinatarios(curso)

arquivo = st.file_uploader("Anexo (opcional)")
if st.button("Enviar"):
    try:
        st.subheader("Prévia:")
        st.write("De:", remetente)
        st.write("Para:", dest_list)
        st.write("Assunto:", assunto)
        st.code(mensagem, language="markdown")

        if arquivo:
            st.write("Anexo:", arquivo.name)
            # Salva no Drive seguindo a estrutura Curso/Turma
            id_salvo, nome_salvo = salvar_arquivo_em_pasta(
                uploaded_file=arquivo,
                nome_arquivo=arquivo.name,
                curso=curso,
                turma=turma,
                pasta_raiz_id=pasta_raiz
            )
            st.success(f"Arquivo salvo no Drive: {nome_salvo}")

        enviar_email_gmail_api(remetente, dest_list, assunto, mensagem, arquivo)
        st.success("E-mail enviado!")

    except Exception as e:
        st.error(f"Erro: {e}")
