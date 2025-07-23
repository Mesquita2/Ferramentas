import streamlit as st
import pandas as pd
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64
import pickle
import os

st.stop()

# Garante que st.session_state["dados"] está inicializado (ajuste conforme seu contexto)
if "dados" not in st.session_state:
    st.session_state["dados"] = {"alunosxdisciplinas": pd.DataFrame()}  # substitua pelo seu dataframe real

df_alunos = st.session_state["dados"].get("alunosxdisciplinas")
df_base = df_alunos.copy()

# Autenticação Gmail com OAuth
@st.cache_resource(show_spinner=False)
def autenticar_gmail_streamlit():
    SCOPES = ['https://www.googleapis.com/auth/gmail.send']
    token_path = "token_gmail.pkl"

    creds = None
    if os.path.exists(token_path):
        with open(token_path, "rb") as token_file:
            creds = pickle.load(token_file)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_config(
            {
                "installed": {
                    "client_id": st.secrets["gmail_oauth"]["client_id"],
                    "client_secret": st.secrets["gmail_oauth"]["client_secret"],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost:8081/"]
                }
            },
            scopes=SCOPES
        )
        creds = flow.run_local_server(port=8081)
        with open(token_path, "wb") as token_file:
            pickle.dump(creds, token_file)

    service = build("gmail", "v1", credentials=creds)
    return service

# Enviar e-mail
def enviar_email_gmail_api(remetente, destinatarios, assunto, mensagem, arquivo=None):
    service = autenticar_gmail_streamlit()

    msg = MIMEMultipart()
    msg["From"] = remetente
    msg["To"] = ", ".join(destinatarios)
    msg["Subject"] = assunto
    msg.attach(MIMEText(mensagem, "plain"))

    if arquivo is not None:
        arquivo.seek(0)  # volta para início do arquivo
        part = MIMEApplication(arquivo.read(), Name=arquivo.name)
        part["Content-Disposition"] = f'attachment; filename="{arquivo.name}"'
        msg.attach(part)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    message = {"raw": raw}

    service.users().messages().send(userId="me", body=message).execute()

# Funções auxiliares
def saudacao():
    hora = datetime.now().hour
    if 5 <= hora < 12:
        return "Bom dia"
    elif 12 <= hora < 18:
        return "Boa tarde"
    return "Boa noite"

def semestres(data_aplicar):
    ano = str(data_aplicar.year)
    mes = data_aplicar.month
    return f"{ano}.01" if 1 <= mes <= 6 else f"{ano}.02"

def create_assunto(curso, disciplina, quantidade, tipo, tipo_prova, data_aplicar, turma):
    assunto = f'Prova iCEV {disciplina} - Tipo {tipo} - {quantidade} cópias, Turma: {turma}'
    cumprimento = saudacao()
    ano = semestres(data_aplicar)
    mensagem = (
        f"{cumprimento}.\n\n"
        "Solicitamos a impressão de:\n\n"
        f"Tipo: {tipo_prova}\n"
        f"Curso/Turma: {curso} {ano} {turma}\n"
        f"Disciplina: {disciplina}\n"
        f"Quantidade: {quantidade} cópias\n\n"
        f"Data: {data_aplicar.strftime('%d/%m/%Y')}"
    )
    return assunto, mensagem

def destinatarios(curso):
    emails = st.secrets["emails"]
    email_cord = st.secrets["email_cord"]

    lista_emails = list(emails.values())

    if curso == "Engenharia de Software":
        lista_emails.append(email_cord["eng"])
    elif curso == "Direito":
        lista_emails.append(email_cord["dir"])
    elif curso == "Administração de Empresas":
        lista_emails.append(email_cord["adm"])

    return lista_emails

# Interface Streamlit
st.title("Envio de E-mail Automático com Anexo")

remetente = st.secrets["email_sis"]["sistema"]

curso = st.selectbox("Escolha o Curso", df_base['CURSO'].unique().tolist())

disciplinas = sorted(df_base[df_base["CURSO"] == curso]["DISCIPLINA"].unique().tolist())
disciplina = st.selectbox("Escolha a disciplina", disciplinas)

turmas_filtradas = df_base[df_base["DISCIPLINA"] == disciplina]["TURMADISC"].unique().tolist()
turma = st.selectbox("Escolha a turma", turmas_filtradas)

df_filtrado = df_base[(df_base["DISCIPLINA"] == disciplina) & (df_base["TURMADISC"] == turma)]
quantidade = df_filtrado['ALUNO'].count() + 5
st.write("Quantidade estimada de cópias:", quantidade)

data_aplicar = st.date_input("Selecione a data", format="DD/MM/YYYY")
st.write("Data selecionada:", data_aplicar.strftime("%d/%m/%Y"))

tipo = st.selectbox("Escolha o tipo da prova", ["Prova", "Recuperação"])
tipo_prova = st.selectbox("Escolha o tipo da prova", ["1", "2"])

assunto, mensagem = create_assunto(curso, disciplina, quantidade, tipo, tipo_prova, data_aplicar, turma)
destinatarios_list = destinatarios(curso)

arquivo = st.file_uploader("Anexar arquivo", type=None)

if st.button("Enviar E-mail"):
    try:
        st.subheader("Prévia do E-mail:")
        st.write("**Remetente:**", remetente)
        st.write("**Destinatário(s):**", destinatarios_list)
        st.write("**Assunto:**", assunto)
        st.write("**Mensagem:**")
        st.code(mensagem, language="markdown")
        if arquivo is not None:
            st.write("**Anexo:**", arquivo.name)

        enviar_email_gmail_api(remetente, destinatarios_list, assunto, mensagem, arquivo)
        st.success("E-mail enviado com sucesso!")
    except Exception as e:
        st.error(f"Erro ao enviar e-mail: {e}")
