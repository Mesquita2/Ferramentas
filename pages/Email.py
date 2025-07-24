import streamlit as st
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import pickle
import os
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SCOPES = ['https://www.googleapis.com/auth/gmail.send']
TOKEN_PATH = "token_gmail.pkl"

# Função para carregar ou gerar credenciais
def carregar_credenciais():
    creds = None
    # Se o token existe, carrega
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)
    # Se token expirou mas tem refresh_token, renova automaticamente
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    # Se não tem token válido, gera novo fluxo
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_config(
            {
                "installed": {
                    "client_id": st.secrets["gmail_oauth"]["client_id"],
                    "client_secret": st.secrets["gmail_oauth"]["client_secret"],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"]
                }
            },
            SCOPES,
        )
        # Aqui, como não tem browser no Streamlit Cloud, usa run_console(), pede código para o usuário
        auth_url, _ = flow.authorization_url(prompt='consent')
        st.write("Por favor, abra o link abaixo no seu navegador para autenticar e copie o código gerado:")
        st.write(auth_url)
        code = st.text_input("Cole o código de autenticação aqui:")
        if code:
            flow.fetch_token(code=code)
            creds = flow.credentials
            with open(TOKEN_PATH, "wb") as token:
                pickle.dump(creds, token)
            st.success("Token salvo com sucesso! Pode enviar o e-mail agora.")
        else:
            st.stop()  # Para esperar o usuário colar o código

    return creds

def criar_servico_gmail():
    creds = carregar_credenciais()
    return build('gmail', 'v1', credentials=creds)

def enviar_email(remetente, destinatarios, assunto, corpo):
    service = criar_servico_gmail()
    message = MIMEMultipart()
    message['to'] = ', '.join(destinatarios)
    message['from'] = remetente
    message['subject'] = assunto
    message.attach(MIMEText(corpo, 'plain'))
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    body = {'raw': raw_message}
    try:
        service.users().messages().send(userId='me', body=body).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao enviar email: {e}")
        return False

# --- Interface Streamlit ---
st.title("Envio de E-mail via Gmail API no Streamlit Cloud")

remetente = st.secrets["email_sis"]["sistema"]
destinatarios_str = st.text_input("Destinatários (separados por vírgula)", "")
assunto = st.text_input("Assunto", "Teste de envio Gmail API")
mensagem = st.text_area("Mensagem", "Olá, este é um teste de envio de e-mail pelo Gmail API.")

if st.button("Enviar E-mail"):
    if not destinatarios_str:
        st.error("Informe ao menos um destinatário.")
    else:
        destinatarios = [e.strip() for e in destinatarios_str.split(",")]
        sucesso = enviar_email(remetente, destinatarios, assunto, mensagem)
        if sucesso:
            st.success("E-mail enviado com sucesso!")
