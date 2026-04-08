import streamlit as st
import pandas as pd
import io
import base64
import time
import pickle
import zipfile
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from googleapiclient.discovery import build


def gerar_excel_unico(df, disciplinas, prova):

    dfs = []

    for disciplina in disciplinas:

        turmas = sorted(
            df[df["DISCIPLINA"] == disciplina]["TURMADISC"].unique()
        )

        for turma in turmas:

            df_filtrado = df[
                (df["DISCIPLINA"] == disciplina) &
                (df["TURMADISC"] == turma)
            ].copy()

            colunas = [
                "CODCOLIGADA",
                "CURSO",
                "DISCIPLINA",
                "TURMADISC",
                "IDTURMADISC",
                "RA",
                "ALUNO"
            ]

            df_filtrado = df_filtrado[colunas]

            df_filtrado[prova] = 0

            dfs.append(df_filtrado)

    df_final = pd.concat(dfs, ignore_index=True)

    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df_final.to_excel(writer, index=False, sheet_name="Notas")

    output.seek(0)
    output.name = f"notas_{prova}_todas_disciplinas.xlsx"

    return output


def carregar():

    st.title("Gerador e Envio de Planilhas de Notas")

    # ==============================
    # Autenticação Gmail
    # ==============================

    token_b64 = st.secrets["gmail_token"]["token_b64"]

    with open("token_gmail.pkl", "wb") as token_file:
        token_file.write(base64.b64decode(token_b64))

    with open("token_gmail.pkl", "rb") as token:
        creds = pickle.load(token)

    @st.cache_resource(show_spinner=False)
    def criar_servico_gmail():
        return build("gmail", "v1", credentials=creds)

    gmail_service = criar_servico_gmail()

    # ==============================
    # Carregar dados
    # ==============================

    df_professor = st.session_state["dados"].get("professores", pd.DataFrame())
    df_alunos = st.session_state["dados"].get("alunosxdisciplinas", pd.DataFrame())

    if df_alunos.empty or df_professor.empty:
        st.warning("Dados de alunos ou professores não carregados.")
        st.stop()

    # padronizar CODDISC
    df_professor["CODDISC"] = df_professor["CODDISC"].astype(str).str.strip()
    df_alunos["CODDISC"] = df_alunos["CODDISC"].astype(str).str.strip()

    # ==============================
    # MERGE alunos + professor
    # ==============================

    df_merge = df_alunos.merge(
        df_professor[["CODDISC", "PROFESSOR", "EMAIL"]],
        on="CODDISC",
        how="left"
    )
    
    df_merge = df_merge.drop_duplicates(
        subset=["RA", "CODDISC", "TURMADISC"]
    )

    # ==============================
    # Seleção de curso
    # ==============================

    cursos = sorted(df_merge["CURSO"].dropna().unique().tolist())

    curso_selecionado = st.selectbox(
        "Escolha o curso",
        cursos
    )

    df_curso = df_merge[df_merge["CURSO"] == curso_selecionado]
    
    # ==============================
    # Seleção de turma (CODTURMA)
    # ==============================
    turmas_curso = sorted(
        df_curso["CODTURMA"].dropna().unique().tolist()
    )

    turmas_selecionadas = st.multiselect(
        "Escolha as turmas",
        turmas_curso
    )

    if turmas_selecionadas:
        df_turma = df_curso[df_curso["CODTURMA"].isin(turmas_selecionadas)]
    else:
        df_turma = pd.DataFrame()
        
    if not turmas_selecionadas:
        st.info("Selecione pelo menos uma turma.")
        st.stop()

    disciplinas_curso = sorted(
        df_turma["DISCIPLINA"].dropna().unique().tolist()
    )

    disciplinas_selecionadas = st.multiselect(
        "Escolha as disciplinas",
        disciplinas_curso
    )

    prova = st.selectbox(
        "Escolha o tipo de prova",
        ["P1", "P2", "FINAL"]
    )

    # ==============================
    # Email assistente
    # ==============================

    email_assistente = st.secrets["email_cord"].get(
        "eng" if "Engenharia" in curso_selecionado else
        "dir" if "Direito" in curso_selecionado else
        "adm"
    )

    if email_assistente:
        st.info(f"Assistente do curso: {email_assistente}")
    else:
        st.warning("Nenhum email de assistente configurado.")

    # ==============================
    # Tabela editável professor/email
    # ==============================

    if disciplinas_selecionadas:

        df_turmas = (
            df_turma[df_turma["DISCIPLINA"].isin(disciplinas_selecionadas)]
            [["CODDISC", "DISCIPLINA", "TURMADISC", "PROFESSOR", "EMAIL"]]
            .drop_duplicates()
            .sort_values(["DISCIPLINA", "TURMADISC"])
        )

        st.subheader("Professores por turma (editável)")

        df_turmas_editado = st.data_editor(
            df_turmas,
            use_container_width=True,
            num_rows="fixed"
        )

    else:
        df_turmas_editado = pd.DataFrame()

    # ==============================
    # Funções auxiliares
    # ==============================

    def gerar_excel(df, disciplina, turma):

        df_filtrado = df[
            (df["DISCIPLINA"] == disciplina) &
            (df["TURMADISC"] == turma)
        ]

        colunas = [
            "CODCOLIGADA",
            "CURSO",
            "TURMADISC",
            "IDTURMADISC",
            "DISCIPLINA",
            "RA",
            "ALUNO"
        ]

        df_filtrado = df_filtrado[colunas]

        df_filtrado[prova] = 0
        df_filtrado[f"QUIZ {prova}"] = None

        output = io.BytesIO()

        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df_filtrado.to_excel(writer, index=False, sheet_name="Notas")

        output.seek(0)
        output.name = f"{disciplina}_{turma}_{prova}.xlsx"

        return output

    def enviar_email(remetente, destinatarios, assunto, mensagem, arquivo):

        msg = MIMEMultipart()

        msg["From"] = remetente
        msg["To"] = ", ".join(destinatarios)
        msg["Subject"] = assunto

        msg.attach(MIMEText(mensagem, "html"))

        part = MIMEApplication(arquivo.read(), Name=arquivo.name)
        part["Content-Disposition"] = f'attachment; filename="{arquivo.name}"'

        msg.attach(part)

        arquivo.seek(0)

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

        gmail_service.users().messages().send(
            userId="me",
            body={"raw": raw}
        ).execute()

    # ==============================
    # Layout botões
    # ==============================

    col1, col2, col3 = st.columns(3)

    # ==============================
    # DOWNLOAD ZIP
    # ==============================

    with col1:

        if st.button("Baixar todas as planilhas (.zip)"):

            buffer_zip = io.BytesIO()

            with zipfile.ZipFile(buffer_zip, "w") as zipf:

                for disciplina in disciplinas_selecionadas:

                    turmas = sorted(
                        df_merge[df_merge["DISCIPLINA"] == disciplina]["TURMADISC"].unique()
                    )

                    for turma in turmas:

                        arquivo_excel = gerar_excel(df_merge, disciplina, turma)

                        zipf.writestr(
                            arquivo_excel.name,
                            arquivo_excel.getvalue()
                        )

            buffer_zip.seek(0)

            st.download_button(
                label="Baixar ZIP",
                data=buffer_zip,
                file_name="planilhas_notas.zip",
                mime="application/zip",
            )

    # ==============================
    # ENVIO EMAIL
    # ==============================

    with col2:

        if st.button("Gerar e enviar planilhas"):

            remetente = "me"
            total_envios = 0

            for _, row in df_turmas_editado.iterrows():

                coddisc = row["CODDISC"]
                disciplina = row["DISCIPLINA"]
                turma = row["TURMADISC"]
                nome_prof = row["PROFESSOR"]
                email_prof = row["EMAIL"]

                st.write(f"Gerando planilha {disciplina} - {turma}")

                arquivo_excel = gerar_excel(df_merge, disciplina, turma)

                corpo_email = f"""
                Olá, <b>{nome_prof}</b>,<br><br>
                Segue em anexo a planilha de notas da turma <b>{turma}</b>
                da disciplina <b>{disciplina}</b> referente à <b>{prova}</b>.<br><br>
                Atenciosamente,<br>
                Equipe Acadêmica.
                """

                try:

                    destinatarios = [email_prof]

                    if email_assistente:
                        destinatarios.append(email_assistente)

                    enviar_email(
                        "me",
                        destinatarios,
                        f"Planilha de Notas - {disciplina} - {turma} - {prova}",
                        corpo_email,
                        arquivo_excel
                    )

                    st.success(
                        f"Enviado para {', '.join(destinatarios)} (Turma {turma})"
                    )

                except Exception as e:

                    st.error(f"Erro na turma {turma}: {e}")

    # ==============================
    # PER ESPECIAL
    # ==============================

    with col3:

        if st.button("PER-ESPECIAL Excel único"):

            arquivo_excel_unico = gerar_excel_unico(
                df=df_merge,
                disciplinas=disciplinas_selecionadas,
                prova=prova
            )

            st.download_button(
                label="Baixar planilha única",
                data=arquivo_excel_unico,
                file_name=arquivo_excel_unico.name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )