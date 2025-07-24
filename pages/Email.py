import streamlit as st
import pandas as pd
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import base64
import pickle
import os

from googleapiclient.discovery import build
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/gmail.send']
TOKEN_PATH = "token_gmail.pkl"

# --- Helpers de autenticação ---
def carregar_credenciais():
    creds = None
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, "rb") as token_file:
            creds = pickle.load(token_file)

    # Se expirou mas tem refresh_token, renova sem pedir login
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    # Se ainda não tem credenciais válidas, faz login manual
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_config(
            {
                "installed": {
                    "client_id": st.secrets["gmail_oauth"]["client_id"],
                    "client_secret": st.secrets["gmail_oauth"]["client_secret"],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost:8080/"]
                }
            },
            scopes=SCOPES
        )
        creds = flow.run_local_server(port=8080, access_type='offline', prompt='consent')
        with open(TOKEN_PATH, "wb") as token_file:
            pickle.dump(creds, token_file)

    return creds

@st.cache_resource(show_spinner=False)
def criar_servico_gmail():
    creds = carregar_credenciais()
    return build("gmail", "v1", credentials=creds)

# --- Fim helpers ---

# Inicializa o DataFrame de alunos, se não estiver carregado
if "dados" not in st.session_state:
    st.session_state["dados"] = {"alunosxdisciplinas": pd.DataFrame()}

df_alunos = st.session_state["dados"].get("alunosxdisciplinas", pd.DataFrame())
df_base = df_alunos.copy()

# Funções de saudação, semestre e assunto (igual ao seu código)
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

def enviar_email_gmail_api(remetente, destinatarios, assunto, mensagem, arquivo=None):
    service = criar_servico_gmail()
    msg = MIMEMultipart()
    msg["From"], msg["To"], msg["Subject"] = remetente, ", ".join(destinatarios), assunto
    msg.attach(MIMEText(mensagem, "plain"))
    if arquivo:
        arquivo.seek(0)
        part = MIMEApplication(arquivo.read(), Name=arquivo.name)
        part["Content-Disposition"] = f'attachment; filename="{arquivo.name}"'
        msg.attach(part)
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()

# --- Interface Streamlit ---
st.title("📧 Envio de Provas por E-mail (Gmail API)")

remetente = st.secrets["email_sis"]["sistema"]

cursos = sorted(df_base['CURSO'].dropna().unique())
curso = st.selectbox("Curso", cursos)

disciplinas = sorted(df_base[df_base["CURSO"]==curso]["DISCIPLINA"].dropna().unique())
disciplina = st.selectbox("Disciplina", disciplinas)

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
        if arquivo: st.write("Anexo:", arquivo.name)
        enviar_email_gmail_api(remetente, dest_list, assunto, mensagem, arquivo)
        st.success("E-mail enviado!")
    except Exception as e:
        st.error(f"Erro: {e}")
