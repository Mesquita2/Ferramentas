import re
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

    df = st.session_state["dados"].get("alunosxdisciplinas")
    df_totvs = df.copy()    
    df_disciplina = st.session_state["dados"].get("disciplina")

    def iniciar_driver():
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")

        # Força usar o chromium do container do Streamlit Cloud
        options.binary_location = "/usr/bin/chromium-browser"

        driver = webdriver.Chrome(
            executable_path="/usr/bin/chromedriver",
            options=options
        )
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
        
    def coletar_envios_detalhado(driver, link_tarefa):
        """Coleta envios de uma tarefa, incluindo email e arquivo."""
        driver.get(link_tarefa)
        time.sleep(3)
        
        try:
            driver.find_element(By.LINK_TEXT, "Ver todos os envios").click()
            time.sleep(3)
            
            rows = driver.find_elements(By.CSS_SELECTOR, "table.generaltable tbody tr")
            dados = []
            
            for row in rows:
                cols = row.find_elements(By.TAG_NAME, "td")
                valores = [c.text.strip() for c in cols]
                
                if len(valores) >= 4:
                    dados.append({
                        "Nome": valores[2],   # Nome do aluno
                        "Email": valores[3],  # Email
                        "Arquivo com Data de Envio": valores[8] if len(valores) > 8 else ""
                    })
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
    
    
    curso = df_totvs['CURSO'].unique().tolist()
    curso = st.selectbox("Escolha o Curso", curso)

    disciplinas = sorted(df_totvs[df_totvs["CURSO"] == curso]["DISCIPLINA"].unique().tolist())
    disciplina = st.selectbox("Escolha a disciplina", disciplinas)

    turmas_filtradas = df_totvs[df_totvs["DISCIPLINA"] == disciplina]["TURMADISC"].unique().tolist()
    turma = st.selectbox("Escolha a turma", turmas_filtradas)

    codigo_disciplina = df_totvs[(df_totvs["DISCIPLINA"] == disciplina) & (df_totvs["TURMADISC"] == turma)]["IDTURMADISC"].unique().tolist()
        
    df_curso = pd.DataFrame(df_disciplina)

    df_curso = df_curso[['NOME', 'IDMOODLE', 'CODTURMA']]

    codigo_disciplina = df_curso[(df_curso["NOME"] == disciplina) & (df_curso['CODTURMA'] == turma)]["IDMOODLE"].tolist()
    curso_id = df_curso[(df_curso["NOME"] == disciplina) & (df_curso['CODTURMA'] == turma)]["CODTURMA"].tolist()
    st.write(f"ID da disciplina: **{codigo_disciplina}**, Turma: **{curso_id}**")
    if curso_id:
        st.write(f"**Link para Aba do Curso:** \nhttps://icev.digital/course/view.php?id={codigo_disciplina[0]}")

    # Botão único para login e tarefas
    if st.button("Conectar e buscar tarefas"):
        if st.session_state.usuario and st.session_state.senha:
            with st.spinner("Conectando ao Moodle..."):
                st.session_state.driver = login_moodle(st.session_state.usuario, st.session_state.senha)
                st.session_state.tarefas = coletar_tarefas(st.session_state.driver, codigo_disciplina[0])

        # Mostra tarefas
        if st.session_state.tarefas:
            df = pd.DataFrame(st.session_state.tarefas, columns=["Tarefa", "Link"])
            st.dataframe(df)
            escolha = st.selectbox("Escolha uma tarefa para ver envios:", df["Tarefa"])

            if escolha:
                link_escolhido = df.loc[df["Tarefa"] == escolha, "Link"].iloc[0]
                envios = coletar_envios_detalhado(st.session_state.driver, link_escolhido)
            if envios:
                    df_envios = pd.DataFrame(envios, columns=["Nome", "Email", "Arquivo com Data de Envio"])
                    st.subheader(":: Envios dos alunos")
                    st.dataframe(df_envios)
                    st.download_button(
                        "Baixar envios",
                        df_envios.to_csv(index=False).encode("utf-8"),
                        "envios.csv",
                        "text/csv"
                    )
                    import io 
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                        df_envios.to_excel(writer, index=False, sheet_name="Envios")
                    output.seek(0)

                    # Monta nome
                    nome_arquivo = f"{curso}_{turma}_{escolha}.xlsx"

                    # Se vier tupla/lista, pega só o primeiro
                    if isinstance(nome_arquivo, (tuple, list)):
                        nome_arquivo = nome_arquivo[0]

                    # Garante string limpa
                    nome_arquivo = str(nome_arquivo)
                    nome_arquivo = re.sub(r'[\\/*?:"<>|\n\r]+', "_", nome_arquivo)

                    # Usa no download
                    st.download_button(
                        label="Gerar e Baixar Planilha Excel",
                        data=output,
                        file_name=nome_arquivo,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

            else:
                st.warning("Nenhum envio encontrado ou sem permissão.")
                
            if st.button("Encerrar sessão"):
                if st.session_state.driver:
                    st.session_state.driver.quit()
                    st.session_state.driver = None

            
