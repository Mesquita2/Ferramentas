from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


import streamlit as st
import pandas as pd
import time
from playwright.sync_api import sync_playwright

def carregar(): 

    def iniciar_browser():
        p = sync_playwright().start()
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        return p, browser, page

    def login_moodle(usuario, senha):
        p, browser, page = iniciar_browser()
        page.goto("https://icev.digital/login/index.php")
        page.fill("#username", usuario)
        page.fill("#password", senha)
        page.click("#loginbtn")
        page.wait_for_load_state("networkidle")
        return p, browser, page
    
    def coletar_tarefas(page, curso_id):
        page.goto(f"https://icev.digital/course/view.php?id={curso_id}")
        page.wait_for_load_state("networkidle")
        tarefas = page.locator("li.activity.assign a")
        resultados = []
        for i in range(tarefas.count()):
            link = tarefas.nth(i)
            resultados.append((link.inner_text(), link.get_attribute("href")))
        return resultados

    def coletar_envios(page, link_tarefa):
        page.goto(link_tarefa)
        page.wait_for_load_state("networkidle")
        try:
            page.click("text=Ver todos os envios")
            page.wait_for_load_state("networkidle")
            linhas = page.locator("table.generaltable tbody tr")
            dados = []
            for i in range(linhas.count()):
                linha = linhas.nth(i)
                colunas = linha.locator("td")
                dados.append([colunas.nth(j).inner_text() for j in range(colunas.count())])
            return dados
        except:
            return []

    # ================== STREAMLIT ==================

    st.title("Moodle – Tarefas e Envios (Scraping com Playwright)")

    if "playwright" not in st.session_state:
        st.session_state.playwright = None
    if "browser" not in st.session_state:
        st.session_state.browser = None
    if "page" not in st.session_state:
        st.session_state.page = None
    if "tarefas" not in st.session_state:
        st.session_state.tarefas = []
    if "usuario" not in st.session_state:
        st.session_state.usuario = ""
    if "senha" not in st.session_state:
        st.session_state.senha = ""

    # Inputs
    st.session_state.usuario = st.text_input("Usuário", value=st.session_state.usuario)
    st.session_state.senha = st.text_input("Senha", type="password", value=st.session_state.senha)
    
    curso_id = st.number_input("ID do Curso", min_value=1, value=2562)

    # Botão único para login e tarefas
    if st.button("Conectar e buscar tarefas"):
        if st.session_state.usuario and st.session_state.senha:
            with st.spinner("Conectando ao Moodle..."):
                st.session_state.playwright, st.session_state.browser, st.session_state.page = login_moodle(
                    st.session_state.usuario, st.session_state.senha
                )
                st.session_state.tarefas = coletar_tarefas(st.session_state.page, curso_id)

    # Mostra tarefas
    if st.session_state.tarefas:
        df = pd.DataFrame(st.session_state.tarefas, columns=["Tarefa", "Link"])
        st.dataframe(df)
        escolha = st.selectbox("Escolha uma tarefa para ver envios:", df["Tarefa"])

        if escolha:
            link_escolhido = df.loc[df["Tarefa"] == escolha, "Link"].iloc[0]
            envios = coletar_envios(st.session_state.page, link_escolhido)
            if envios:
                df_envios = pd.DataFrame(envios)
                st.subheader("Envios dos alunos")
                st.dataframe(df_envios)
                st.download_button(
                    "Baixar envios",
                    df_envios.to_csv(index=False).encode("utf-8"),
                    "envios.csv",
                    "text/csv"
                )
            else:
                st.warning("Nenhum envio encontrado ou sem permissão.")
