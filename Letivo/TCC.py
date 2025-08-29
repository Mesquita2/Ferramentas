import re
import streamlit as st
import pandas as pd
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


def carregar(): 

    df = st.session_state["dados"].get("alunosxdisciplinas")
    df_totvs = df.copy()    
    df_disciplina = st.session_state["dados"].get("disciplina")

    # ---------- Selenium ----------
    def iniciar_driver():
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
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
    
    def coletar_tarefas(driver, curso_id):
        driver.get(f"https://icev.digital/course/view.php?id={curso_id}")
        time.sleep(3)
        tarefas = driver.find_elements(By.CSS_SELECTOR, "li.activity.assign a")
        return [(t.text, t.get_attribute("href")) for t in tarefas]

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

    # ---------- Streamlit ----------
    st.title("Moodle – Tarefas e Envios (Scraping)")

    if "driver" not in st.session_state:
        st.session_state.driver = None
    if "tarefas" not in st.session_state:
        st.session_state.tarefas = []
    if "usuario" not in st.session_state:
        st.session_state.usuario = ""
    if "senha" not in st.session_state:
        st.session_state.senha = ""

    # Login
    st.session_state.usuario = st.text_input("Usuário", value=st.session_state.usuario)
    st.session_state.senha = st.text_input("Senha", type="password", value=st.session_state.senha)

    curso = st.selectbox("Escolha o Curso", df_totvs['CURSO'].unique().tolist())
    turmas_filtradas = df_totvs[df_totvs["CURSO"] == curso]["TURMADISC"].unique().tolist()
    turma = st.selectbox("Escolha a turma", turmas_filtradas)

    disciplinas = sorted(df_totvs[df_totvs["TURMADISC"] == turma]["DISCIPLINA"].unique().tolist())
    disciplinas_selecionadas = st.multiselect("Escolha as disciplinas", disciplinas)

    df_curso = pd.DataFrame(df_disciplina)[['NOME', 'IDMOODLE', 'CODTURMA']]

    # Pega os IDs Moodle de todas as disciplinas selecionadas
    ids_disciplinas = df_curso[
        (df_curso["NOME"].isin(disciplinas_selecionadas)) & 
        (df_curso['CODTURMA'] == turma)
    ]["IDMOODLE"].tolist()

    if ids_disciplinas:
        st.write("IDs Moodle encontrados:")
        for d, c_id in zip(disciplinas_selecionadas, ids_disciplinas):
            st.write(f"- **{d}** → {c_id} | [Abrir curso](https://icev.digital/course/view.php?id={c_id})")

    # Botão único para login e tarefas
    if st.button("Conectar e buscar tarefas"):
        if st.session_state.usuario and st.session_state.senha:
            with st.spinner("Conectando ao Moodle..."):
                st.session_state.driver = login_moodle(st.session_state.usuario, st.session_state.senha)

                resultados = []
                for nome_disc, c_id in zip(disciplinas_selecionadas, ids_disciplinas):
                    tarefas = coletar_tarefas(st.session_state.driver, c_id)
                    for tarefa, link in tarefas:
                        resultados.append({
                            "Disciplina": nome_disc,
                            "Tarefa": tarefa,
                            "Link": link
                        })
                st.session_state.tarefas = resultados

        # Mostra todas as tarefas de todas as disciplinas
        if st.session_state.tarefas:
            df = pd.DataFrame(st.session_state.tarefas)
            st.dataframe(df)
            escolha = st.selectbox("Escolha uma tarefa para ver envios:", df["Tarefa"].unique())

            if escolha:
                link_escolhido = df.loc[df["Tarefa"] == escolha, "Link"].iloc[0]
                envios = coletar_envios_detalhado(st.session_state.driver, link_escolhido)

                if envios:
                    df_envios = pd.DataFrame(envios)
                    st.subheader(":: Envios dos alunos")
                    st.dataframe(df_envios)

                    import io 
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                        df_envios.to_excel(writer, index=False, sheet_name="Envios")
                    output.seek(0)

                    nome_arquivo = f"{curso}_{turma}_{escolha}.xlsx"
                    nome_arquivo = re.sub(r'[\\/*?:"<>|\n\r]+', "_", str(nome_arquivo))

                    st.download_button(
                        label="Gerar e Baixar Planilha Excel",
                        data=output,
                        file_name=nome_arquivo,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            else:
                st.warning("Nenhum envio encontrado ou sem permissão.")
