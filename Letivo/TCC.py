import streamlit as st
import pandas as pd
import time

#playwright e selenium

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

def carregar(): 
    
    def iniciar_driver():
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920x1080")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        return driver

    def login_moodle(usuario, senha):
        driver = iniciar_driver()
        driver.get("https://icev.digital/login/index.php")
        time.sleep(2)
        driver.find_element(By.ID, "username").send_keys(usuario)
        driver.find_element(By.ID, "password").send_keys(senha)
        driver.find_element(By.ID, "loginbtn").click()
        time.sleep(3)
        return driver
    
    def baixar_arquivos(driver, link):
        driver.get(link)
        time.sleep(3)
        arquivos = driver.find_elements(By.CSS_SELECTOR, "a[href*='pluginfile.php']")
        for arquivo in arquivos:
            arquivo.click()
            time.sleep(1)   

    def coletar_tarefas(driver, curso_id):
        driver.get(f"https://icev.digital/course/view.php?id={curso_id}")
        time.sleep(3)
        tarefas = driver.find_elements(By.CSS_SELECTOR, "li.activity.assign a")
        return [(t.text, t.get_attribute("href")) for t in tarefas]

    def coletar_envios(driver, link_tarefa):
        driver.get(link_tarefa)
        time.sleep(3)
        try:
            driver.find_element(By.LINK_TEXT, "Ver todos os envios").click()
            time.sleep(3)
            linhas = driver.find_elements(By.CSS_SELECTOR, "table.generaltable tbody tr")
            dados = [[c.text for c in linha.find_elements(By.TAG_NAME, "td")] for linha in linhas if linha]
            return dados
        except:
            return []

    # ================== STREAMLIT ==================

    st.title("Moodle – Tarefas e Envios (Scraping)")


    if "driver" not in st.session_state:
        st.session_state.driver = None
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
                st.session_state.driver = login_moodle(st.session_state.usuario, st.session_state.senha)
                st.session_state.tarefas = coletar_tarefas(st.session_state.driver, curso_id)

    # Mostra tarefas
    if st.session_state.tarefas:
        df = pd.DataFrame(st.session_state.tarefas, columns=["Tarefa", "Link"])
        st.dataframe(df)
        escolha = st.selectbox("Escolha uma tarefa para ver envios:", df["Tarefa"])

        if escolha:
            link_escolhido = df.loc[df["Tarefa"] == escolha, "Link"].iloc[0]
            envios = coletar_envios(st.session_state.driver, link_escolhido)
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
        
