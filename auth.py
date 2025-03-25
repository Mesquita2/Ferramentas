import streamlit as st

def check_authentication():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        st.warning("Faça login para acessar esta funcionalidade.")
        login_form()
        return False
    return True

def login_form():
    users = st.secrets["authentication"]  # Obtém lista de usuários e senhas

    with st.form("login_form"):
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        submit_button = st.form_submit_button("Entrar")

        if submit_button:
            if username in users and users[username] == password:
                st.session_state.authenticated = True
                st.success(f"Bem-vindo, {username}!")
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

def logout():
    st.session_state.authenticated = False
    st.rerun()
