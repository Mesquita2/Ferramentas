import streamlit as st
import pandas as pd
import io
from auth import check_authentication

st.markdown(
    """
    <h1 style='color:gold; font-size: 64px; text-align: center;'>Em Manutenção</h1>
    """,
    unsafe_allow_html=True
)
st.stop()


# Configuração da página
st.set_page_config(page_title="Analise de Quiz",
                   page_icon="", 
                   layout="wide")

if not check_authentication():
    st.stop()
    
df_base = st.session_state["dados"].get("alunosxdisciplinas").copy()

# Função para conectar ao banco com cache
def limpar(df):
    # Remove status C
    df = df[df['CODSTATUS'] != 'C'].copy()

    # Filtra CODTURMA que começa com "03"
    df = df[df['CODTURMA'].astype(str).str.startswith("03")].copy()

    # Remove duplicatas por DISCIPLINA + RA
    df = df.drop_duplicates(subset=['DISCIPLINA', 'RA']).reset_index(drop=True)

    # Contagem por DISCIPLINA
    contagem = df['DISCIPLINA'].value_counts().reset_index()
    contagem.columns = ['DISCIPLINA', 'QUANTIDADE']
    
    return contagem

def simulado(df):
    # Remove status C
    df = df[df['CODSTATUS'] != 'C'].copy()

    # Filtra CODTURMA que começa com "03"
    df = df[df['CODTURMA'].astype(str).str.startswith("03")].copy()

    # Remove duplicatas por DISCIPLINA + RA
    df = df.drop_duplicates(subset=['CODTURMA', 'RA']).reset_index(drop=True)

    # Contagem por DISCIPLINA
    contagem = df['CODTURMA'].value_counts().reset_index()
    contagem.columns = ['CODTURMA', 'QUANTIDADE']
    
    return contagem

# Curso alvo
curso_alvo = "Bacharelado em Engenharia de Software"


if "dados" in st.session_state and "testes" in st.session_state["dados"]:
    df_recP1 = st.session_state["dados"]["recP1_analise"].copy()
    df_recP2 = st.session_state["dados"]["recP2_analise"].copy()
    df_recfinal = st.session_state["dados"]["rec_simulado"].copy()
else:
    st.error("Arquivo 'testes.xlsx' não encontrado em st.session_state['dados'].")
    st.stop()
    
P1 = limpar(df_recP1)
P2 = limpar(df_recP2)
final = simulado(df_recfinal)


st.write("REC P1", P1)
st.write("REC P2", P2)
st.write("REC FINAL", final)