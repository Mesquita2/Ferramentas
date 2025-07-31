import streamlit as st
from streamlit_option_menu import option_menu
from auth import check_authentication, logout
import Letivo.Inicial as Inicio
from Pg_Simulado import REC_Simulado, Simulado_2, Simulado_Faltantes, Simulado_Teste

st.set_page_config(page_title="Sistema", layout="wide")

if check_authentication():

    with st.sidebar:
        escolha = option_menu("Menu", ["REC_Simulado", "Simulado_2", "Simulado_Faltantes", "Simulado_Teste", "Sair"],
                              icons=[],
                              menu_icon="cast", default_index=0)

    if escolha == "REC_Simulado":
        REC_Simulado.carregar()
    elif escolha == "Simulado_2":
        Simulado_2.carregar()   
    elif escolha == "Simulado_Faltantes":
        Simulado_Faltantes.carregar()
    elif escolha == "Simulado_Teste":
        Simulado_Teste.carregar()