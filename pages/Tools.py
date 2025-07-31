import streamlit as st
from streamlit_option_menu import option_menu
from auth import check_authentication, logout
import Letivo.Inicial as Inicio
from Utils import DNT_oficinas, QR_Code, Z_Analise_Quiz

st.set_page_config(page_title="Sistema", layout="wide")

if check_authentication():

    with st.sidebar:
        escolha = option_menu("Menu", ["DNT_oficinas", "QR_Code", "Z_Analise_Quiz"],
                              icons=["bar-chart-line", "qr-code", "bar-chart-line"],
                              menu_icon="cast", default_index=0)

    if escolha == "DNT_oficinas":
        DNT_oficinas.carregar()
    elif escolha == "QR_Code":
        QR_Code.carregar()
    elif escolha == "Z_Analise_Quiz":
        Z_Analise_Quiz.carregar()
    elif escolha == "Sair":
        logout()
