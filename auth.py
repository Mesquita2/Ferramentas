import streamlit as st
from datetime import datetime, timedelta
from google_auth_oauthlib.flow import InstalledAppFlow
import pickle

MAX_TENTATIVAS = 3
BLOQUEIO_SEGUNDOS = 60

def check_authentication():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        st.warning("Faça login para acessar esta funcionalidade.")
        login_form()
        return False
    return True

def login_form():
    users = st.secrets["authentication"]

    if "tentativas" not in st.session_state:
        st.session_state.tentativas = 0
    if "bloqueado_ate" not in st.session_state:
        st.session_state.bloqueado_ate = None

    if st.session_state.bloqueado_ate:
        agora = datetime.now()
        if agora < st.session_state.bloqueado_ate:
            restante = (st.session_state.bloqueado_ate - agora).seconds
            st.error(f"Tentativas excedidas. Tente novamente em {restante} segundos.")
            return
        else:
            st.session_state.tentativas = 0
            st.session_state.bloqueado_ate = None

    with st.form("login_form"):
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        submit_button = st.form_submit_button("Entrar")

        if submit_button:
            if username in users and users[username] == password:
                st.session_state.authenticated = True
                st.session_state.tentativas = 0 
                st.success(f"Bem-vindo, {username}!")
                st.rerun()
            else:                
                st.session_state.tentativas += 1
                st.error("Usuário ou senha incorretos.")
                 
                #st.session_state.username = ""
                #st.session_state.password = ""

                if st.session_state.tentativas >= MAX_TENTATIVAS:
                    st.session_state.bloqueado_ate = datetime.now() + timedelta(seconds=BLOQUEIO_SEGUNDOS)
                    st.error(f"Você excedeu o número de tentativas. Tente novamente em {BLOQUEIO_SEGUNDOS} segundos.")
                    
                    #st.rerun()    

def logout():
    st.session_state.authenticated = False
    st.rerun()
    
    from google_auth_oauthlib.flow import InstalledAppFlow
import pickle
import streamlit as st
import os

SCOPES = ['https://www.googleapis.com/auth/gmail.send']

client_config = {
    "installed": {
        "client_id": st.secrets["gmail_oauth"]["client_id"],
        "client_secret": st.secrets["gmail_oauth"]["client_secret"],
        "auth_uri": st.secrets["gmail_oauth"]["auth_uri"],
        "token_uri": st.secrets["gmail_oauth"]["token_uri"],
        "redirect_uris": st.secrets["gmail_oauth"]["redirect_uris"],
    }
}

def salvar_token_gmail():
    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_console()
    with open("token_gmail.pkl", "wb") as token_file:
        pickle.dump(creds, token_file)
    print("Token salvo em token_gmail.pkl")


