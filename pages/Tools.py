import streamlit as st
from streamlit_option_menu import option_menu
from auth import check_authentication, logout
from Utils import DNT_oficinas, QR_Code, analise_google,Dimmy_Dash, PosDash
from carregamento import carregar_drive, limpeza_alunos_disciplinas

st.set_page_config(page_title="Sistema", layout="wide")

if check_authentication():

    carregar_drive()

    df_alunos = st.session_state["dados"]["alunosxdisciplinas"]
    df_limpo = limpeza_alunos_disciplinas(df_alunos)
    st.session_state["dados"]["alunosxdisciplinas"] = df_limpo

    with st.sidebar:
        escolha = option_menu("Menu", ["DNT oficinas", "QR Code", "Analise Google", "Dimmy Dash", "Pos Dash"],
                              icons=["bar-chart-line", "qr-code", "bar-chart-line", "clipboard-pulse", "clipboard-pulse"],
                              menu_icon="cast", default_index=0)

    if escolha == "DNT oficinas":
        DNT_oficinas.carregar()
    if escolha == "QR Code":
        QR_Code.carregar()
    if escolha == "Analise Google":
        analise_google.carregar()
    if escolha == "Dimmy Dash":
        Dimmy_Dash.carregar() 
    if escolha == "Pos Dash":
        PosDash.carregar()
    if escolha == "Sair":
        logout()
