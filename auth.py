import streamlit as st

def check_authentication(username, password):
    try:
        users = st.secrets["authentication"]  # Obtém a lista de usuários do secrets.toml
        return username in users and users[username] == password
    except KeyError:
        st.error("Erro ao carregar credenciais. Verifique o arquivo secrets.toml.")
        return False

def login_form():
    st.title("Login")
    
    with st.form("login_form"):
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        submit_button = st.form_submit_button("Entrar")

        if submit_button:
            if check_authentication(username, password):
                st.session_state.authenticated = True
                st.success(f"Bem-vindo, {username}!")
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

# Verifica se o usuário já está autenticado antes de exibir o login
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    login_form()
else:
    st.write("Você já está logado!")
