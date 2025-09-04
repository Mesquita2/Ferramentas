import streamlit as st
from streamlit_option_menu import option_menu
from auth import check_authentication, logout
import Letivo.Inicial as Inicio
from Pg_Simulado import REC_Simulado, Simulado_2, Simulado_Faltantes, Simulado_Teste, Calculo
from Letivo.Inicial import carregar_drive
from carregamento import carregar_drive, limpeza_alunos_disciplinas

st.set_page_config(page_title="Sistema", layout="wide")

if check_authentication():
    
    carregar_drive()
    
    df_alunos = st.session_state["dados"]["alunosxdisciplinas"]
    df_limpo = limpeza_alunos_disciplinas(df_alunos)
    st.session_state["dados"]["alunosxdisciplinas"] = df_limpo

    with st.sidebar:
        escolha = option_menu("Menu", ["REC_Simulado", "Simulado_2", "Simulado_Faltantes", "Simulado_Teste", "Apenas Calculo"],
                              icons=["", "", "", ""],
                              menu_icon="cast", default_index=0)

    if escolha == "REC_Simulado":
        REC_Simulado.carregar()
    elif escolha == "Simulado_2":
        Simulado_2.carregar()   
    elif escolha == "Simulado_Faltantes":
        Simulado_Faltantes.carregar()
    elif escolha == "Simulado_Teste":
        Simulado_Teste.carregar()
    elif escolha == "Apenas Calculo":
        Calculo.carregar()