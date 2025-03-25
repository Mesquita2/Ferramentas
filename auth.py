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
    with st.form("login_form"):
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        submit_button = st.form_submit_button("Entrar")

        # Obtém credenciais do secrets.toml
        stored_username = st.secrets["authentication"]["username"]
        stored_password = st.secrets["authentication"]["password"]

        if submit_button:
            if username == stored_username and password == stored_password:
                st.session_state.authenticated = True
                st.success("Login realizado com sucesso!")
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

def logout():
    st.session_state.authenticated = False
    st.rerun()
