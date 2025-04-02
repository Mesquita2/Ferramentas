import smtplib
import streamlit as st
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import pandas as pd
import logging
import os

# Configurar logs
tmp_log_file = "email_errors.log"
logging.basicConfig(filename=tmp_log_file, level=logging.ERROR)

# Função para carregar os alunos do arquivo Excel
def carregar_alunos():
    try:
        df = pd.read_excel("alunos.xlsx", dtype={"RA": str})
        df.rename(columns={'NOMEDISCIPLINA': 'DISCIPLINA',
                           'NOMECURSO': 'CURSO',
                           'NOMEALUNO': 'ALUNO',
                           'TURMADISC': 'TURMADISC'}, inplace=True)
        return df
    except Exception as e:
        st.error("Erro ao carregar o arquivo alunos.xlsx. Verifique o arquivo e tente novamente.")
        logging.error(f"Erro ao carregar alunos.xlsx: {e}")
        return pd.DataFrame()

# Função para enviar e-mail via SMTP
def enviar_email_smtp(destinatario, assunto, mensagem, arquivo=None):
    try:
        smtp_server = st.secrets["email"]["smtp_server"]
        smtp_port = st.secrets["email"]["smtp_port"]
        remetente = st.secrets["email"]["remetente"]
        senha = st.secrets["email"]["senha"]

        if not destinatario.endswith("@somosicev.com"):
            st.error("Apenas e-mails institucionais são permitidos!")
            return

        # Criar a mensagem do e-mail
        msg = MIMEMultipart()
        msg["From"] = remetente
        msg["To"] = destinatario
        msg["Subject"] = assunto
        msg.attach(MIMEText(mensagem, "plain"))

        # Adicionar anexo (se houver)
        if arquivo:
            if len(arquivo.getvalue()) > 5 * 1024 * 1024:  # Limite de 5MB
                st.error("O arquivo excede o limite de 5MB.")
                return

            anexo = MIMEBase("application", "octet-stream")
            anexo.set_payload(arquivo.getvalue())
            encoders.encode_base64(anexo)
            anexo.add_header("Content-Disposition", f"attachment; filename={arquivo.name}")
            msg.attach(anexo)

        # Conectar ao servidor SMTP e enviar e-mail
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(remetente, senha)
            server.sendmail(remetente, destinatario, msg.as_string())

        st.success("E-mail enviado com sucesso!")

    except Exception as e:
        st.error(f"Erro ao enviar e-mail: {e}")
        logging.error(f"Erro ao enviar e-mail via SMTP: {e}")

# Interface Streamlit
st.title("Escolher disciplina para enviar para mecanografia")

df_alunos = carregar_alunos()
if df_alunos.empty:
    st.stop()

disciplinas = df_alunos["DISCIPLINA"].unique().tolist()
disciplina = st.selectbox("\U0001F4D6 Escolha a disciplina", disciplinas)

turmas_filtradas = df_alunos[df_alunos["DISCIPLINA"] == disciplina]["TURMADISC"].unique().tolist()
turma = st.selectbox("\U0001F3EB Escolha a turma", turmas_filtradas)

prova = st.selectbox("Escolha se é P1 ou P2", ["P1", "P2"])

df_filtrado = df_alunos[(df_alunos["DISCIPLINA"] == disciplina) & (df_alunos["TURMADISC"] == turma)]
num_alunos = df_filtrado["RA"].nunique()

st.write(f"\U0001F4DD **Alunos da Disciplina: {disciplina} | Turma: {turma}** (Total: {num_alunos} alunos)")

st.title("Enviar E-mail com Anexo")
email = st.text_input("Destinatário")
assunto = st.text_input("Assunto")
mensagem = st.text_area("Mensagem")
arquivo = st.file_uploader("\U0001F4CE Escolha um arquivo para anexar")

smtp_server = st.secrets["email"]["smtp_server"]
smtp_port = st.secrets["email"]["smtp_port"]

st.write(f"Servidor SMTP: {smtp_server}")
st.write(f"Porta SMTP: {smtp_port}")

if st.button("Enviar"):
    if email and assunto and mensagem:
        enviar_email_smtp(email, assunto, mensagem, arquivo)
    else:
        st.warning("Preencha todos os campos!")
