import streamlit as st
import pandas as pd
import io
from auth import check_authentication
import mysql.connector

st.write("Em manutenção")
st.stop()

# Configuração da página
st.set_page_config(page_title="Analise de Quiz",
                   page_icon="", 
                   layout="wide")

if not check_authentication():
    st.stop()

# Função para conectar ao banco com cache
@st.cache_resource
def get_connection():
    try:
        return mysql.connector.connect(
            host=st.secrets["database"]["host"],
            port=st.secrets["database"]["port"],
            database=st.secrets["database"]["name"],
            user=st.secrets["database"]["user"],
            password=st.secrets["database"]["password"]
        )
    except mysql.connector.Error as err:
        st.error(f"Erro ao conectar no banco: {err}")
        raise

# Chamada da conexão
conn = get_connection()
