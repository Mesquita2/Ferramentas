import streamlit as st
import pandas as pd
import io
import base64
import time
import pickle
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from googleapiclient.discovery import build


def carregar():
    st.title("Gerador e Envio de Planilhas de Notas")

    # === Autenticação Gmail ===
    token_b64 = st.secrets["gmail_token"]["token_b64"]
    with open("token_gmail.pkl", "wb") as token_file:
        token_file.write(base64.b64decode(token_b64))
    with open("token_gmail.pkl", "rb") as token:
        creds = pickle.load(token)

    @st.cache_resource(show_spinner=False)
    def criar_servico_gmail():
        return build("gmail", "v1", credentials=creds)

    gmail_service = criar_servico_gmail()

    # === Dados carregados ===
    df_professor = st.session_state["dados"].get("professores", pd.DataFrame())
    df_alunos = st.session_state["dados"].get("alunosxdisciplinas", pd.DataFrame())

    if df_alunos.empty or df_professor.empty:
        st.warning(" Dados de alunos ou professores não carregados.")
        st.stop()

    # === Seleção de curso e disciplinas ===
    cursos = sorted(df_alunos["CURSO"].dropna().unique().tolist())
    curso_selecionado = st.selectbox("Escolha o curso", cursos)

    disciplinas_curso = sorted(
        df_alunos[df_alunos["CURSO"] == curso_selecionado]["DISCIPLINA"].dropna().unique().tolist()
    )
    disciplinas_selecionadas = st.multiselect("Escolha as disciplinas", disciplinas_curso)

    prova = st.selectbox("Escolha o tipo de prova", ["P1", "P2", "FINAL"])

    # === Assistente do curso (vindo do secrets) ===
    email_assistente = st.secrets["email_cord"].get(
        "eng" if "Engenharia" in curso_selecionado else
        "dir" if "Direito" in curso_selecionado else
        "adm"
    )

    if not email_assistente:
        st.warning(" Nenhum e-mail de assistente configurado para este curso.")
    else:
        st.info(f" Assistente do curso: {email_assistente}")

    # === Funções auxiliares ===
    def gerar_excel(df, disciplina, turma):
        df_filtrado = df[(df["DISCIPLINA"] == disciplina) & (df["TURMADISC"] == turma)]
        colunas = ["CODCOLIGADA", "CURSO", "TURMADISC", "IDTURMADISC", "DISCIPLINA", "RA", "ALUNO"]
        df_filtrado = df_filtrado[colunas]
        df_filtrado["P1"] = 0
        df_filtrado["QUIZ P1"] = None

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
        msg.attach(MIMEText(mensagem, "plain"))

        part = MIMEApplication(arquivo.read(), Name=arquivo.name)
        part["Content-Disposition"] = f'attachment; filename="{arquivo.name}"'
        msg.attach(part)
        arquivo.seek(0)

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        gmail_service.users().messages().send(userId="me", body={"raw": raw}).execute()

    # === Botão único para envio ===
    if st.button("Gerar e enviar planilhas para todas as disciplinas selecionadas"):
        remetente = "me"
        total_envios = 0

        for disciplina in disciplinas_selecionadas:
            st.markdown(f"### {disciplina}")
            prof_disciplina = df_professor[df_professor["DISCIPLINA"] == disciplina]

            if prof_disciplina.empty:
                st.warning(f"Nenhum professor encontrado para {disciplina}.")
                continue

            nome_prof = prof_disciplina.iloc[0]["PROFESSOR"]
            email_prof = prof_disciplina.iloc[0]["EMAIL"]

            turmas = sorted(df_alunos[df_alunos["DISCIPLINA"] == disciplina]["TURMADISC"].unique())

            for turma in turmas:
                st.write(f"Gerando planilha para **{turma}**...")
                arquivo_excel = gerar_excel(df_alunos, disciplina, turma)

                corpo_email = (
                    f"Olá, {nome_prof},\n\n"
                    f"Segue em anexo a planilha de notas da turma *{turma}* "
                    f"da disciplina *{disciplina}* referente à *{prova}*.\n\n"
                    "Atenciosamente,\nEquipe Acadêmica."
                )

                try:
                    destinatarios = [email_prof]
                    if email_assistente:
                        destinatarios.append(email_assistente)

                    corpo = enviar_email(
                        remetente=remetente,
                        destinatarios=destinatarios,
                        assunto=f"Planilha de Notas - {disciplina} - {turma} - {prova}",
                        mensagem=corpo_email,
                        arquivo=arquivo_excel,
                    )
                    
                    st.write(f"Enviado... \n{corpo}")

                    total_envios += 1
                    st.success(f" Enviado para {', '.join(destinatarios)} (Turma {turma})")
                except Exception as e:
                    st.error(f" Falha ao enviar planilha da turma {turma}: {e}")

                time.sleep(1.5)

        st.success(f" Processo concluído! {total_envios} e-mails enviados com sucesso.")
