import streamlit as st
from streamlit_option_menu import option_menu
from auth import check_authentication, logout
import Letivo.Inicial as Inicio
from Letivo import ConversorTotvs, Email, Rec, Relatorio_Status, GerarPlanilhas, Quizz, TCC

st.set_page_config(page_title="Sistema", layout="wide")

if check_authentication():

    with st.sidebar:
        escolha = option_menu("Letivo", ["Início", "Email", "Planilhas", "Conversor Notas Totvs","Quizz", "Rec", "Relatório Status", "TCC - Analise" ,"Sair"],
                              icons=["house", "envelope", "download","upload","upload", "box-arrow-right", "arrow-repeat", "bar-chart", "box-arrow-right"],
                              menu_icon="cast", default_index=0)

    if escolha == "Início":
        Inicio.carregar()

    if escolha == "Email":
        Email.carregar()
    
    if escolha == "Planilhas":
        GerarPlanilhas.carregar()

    if escolha == "Conversor Notas Totvs":
        ConversorTotvs.carregar()
        
    if escolha == "Quizz":
        Quizz.carregar()
        
    if escolha == "Rec":
        Rec.carregar()  
        
    if escolha == "Relatório Status": 
        Relatorio_Status.carregar()
        
    if escolha == "TCC - Analise":
        TCC.carregar()

    if escolha == "Sair":
        logout()
