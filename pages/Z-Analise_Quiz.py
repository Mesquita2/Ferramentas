import streamlit as st
import pandas as pd
import io
from auth import check_authentication

# Configuração da página
st.set_page_config(page_title="Analise de Quiz",
                   page_icon="", 
                   layout="wide")

if not check_authentication():
    st.stop()

# Função para conectar ao banco com cache

if "dados" in st.session_state and "testes" in st.session_state["dados"]:
    df = st.session_state["dados"]["testes"].copy()
else:
    st.error("Arquivo 'testes.xlsx' não encontrado em st.session_state['dados'].")
    st.stop()

# Filtra apenas os dados do curso "Engenharia de Software"
df_eng = df[df['NOMECURSO'] == 'Engenharia de Software']

# Seleciona apenas as colunas desejadas e remove duplicatas
df_unicos = df_eng[['NOMEDISCIPLINA', 'IDMOODLE']].drop_duplicates()
st.write(df_unicos)

# Se quiser exportar para um novo CSV:
df_unicos.to_csv("disciplinas_eng_software.csv", index=False)

# Se quiser apenas a lista de IDMOODLE:
lista_ids = df_unicos['IDMOODLE'].dropna().unique().tolist()

st.write(lista_ids)
