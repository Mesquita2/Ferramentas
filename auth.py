import streamlit as st

def check_authentication():
    """Verifica se o usuário está autenticado antes de permitir o acesso."""
    if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
        st.sidebar.header("Login")
        username = st.sidebar.text_input("Usuário")
        password = st.sidebar.text_input("Senha", type="password")

        users = st.secrets["auth"]  # Obtém usuários do secrets.toml

        if username in users and users[username] == password:
            st.session_state["authenticated"] = True
            st.sidebar.success("Login bem-sucedido! ✅")
            st.rerun()
        else:
            st.sidebar.error("Usuário ou senha incorretos!")
            st.stop()  # Interrompe a execução até que o login seja feito
