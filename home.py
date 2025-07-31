import streamlit as st
from streamlit_option_menu import option_menu
from auth import check_authentication, logout
import Letivo.Inicial as Inicio
from Letivo import ConversorTotvs, Email, Rec, Relatorio_Status, GerarPlanilhas, Quizz

st.set_page_config(page_title="Sistema", layout="wide")

if check_authentication():

    with st.sidebar:
        escolha = option_menu("Letivo", ["Início", "Email", "Planilhas", "Conversor Notas Totvs","Quizz", "Rec", "Relatório Status" ,"Sair"],
                              icons=["house", "envelope", "download","upload","upload", "box-arrow-right", "arrow-repeat", "bar-chart", "box-arrow-right"],
                              menu_icon="cast", default_index=0)

    if escolha == "Início":
        Inicio.carregar()

    elif escolha == "Email":
        Email.carregar()
    
    elif escolha == "Planilhas":
        GerarPlanilhas.carregar()

    elif escolha == "Conversor Notas Totvs":
        ConversorTotvs.carregar()
        
    elif escolha == "Quizz":
        Quizz.carregar()
        
    elif escolha == "Rec":
        Rec.carregar()  
        
    elif escolha == "Relatório Status": 
        Relatorio_Status.carregar()

    elif escolha == "Sair":
        logout()
