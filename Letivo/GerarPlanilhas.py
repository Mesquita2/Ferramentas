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

    # === Dados carregados do estado ===
    df_professor = st.session_state["dados"].get("professores", pd.DataFrame())
    df_alunos = st.session_state["dados"].get("alunosxdisciplinas", pd.DataFrame())

    if df_alunos.empty or df_professor.empty:
        st.warning(" Dados de alunos ou professores não carregados.")
        st.stop()

    # === 🎓 Seleciona curso, disciplina e prova ===
    # Lista e escolhe o curso
    cursos = sorted(df_alunos["CURSO"].dropna().unique().tolist())
    curso_selecionado = st.selectbox("Escolha o curso", cursos)

    # Filtra as disciplinas apenas do curso selecionado
    disciplinas_curso = (
        df_alunos[df_alunos["CURSO"] == curso_selecionado]["DISCIPLINA"]
        .dropna()
        .unique()
        .tolist()
    )
    disciplinas_curso = sorted(disciplinas_curso)
    disciplina = st.selectbox("Escolha a disciplina", disciplinas_curso)

    # Escolhe o tipo de prova
    prova = st.selectbox("Escolha o tipo de prova", ["P1", "P2", "FINAL"])

    # === Identifica o professor responsável ===
    prof_disciplina = df_professor[df_professor["DISCIPLINA"] == disciplina]

    if prof_disciplina.empty:
        st.warning("Nenhum professor encontrado para esta disciplina.")
        st.stop()

    nome_prof = prof_disciplina.iloc[0]["PROFESSOR"]
    email_prof = prof_disciplina.iloc[0]["EMAIL"]

    st.markdown(f"**Professor responsável:** {nome_prof}  \n{email_prof}")

    # === Gera planilhas individuais por turma ===
    turmas = sorted(df_alunos[df_alunos["DISCIPLINA"] == disciplina]["TURMADISC"].unique())

    def gerar_excel(df, turma):
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

    def enviar_email(remetente, destinatario, assunto, mensagem, arquivo):
        msg = MIMEMultipart()
        msg["From"] = remetente
        msg["To"] = destinatario
        msg["Subject"] = assunto
        msg.attach(MIMEText(mensagem, "plain"))

        part = MIMEApplication(arquivo.read(), Name=arquivo.name)
        part["Content-Disposition"] = f'attachment; filename="{arquivo.name}"'
        msg.attach(part)
        arquivo.seek(0)

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        gmail_service.users().messages().send(userId="me", body={"raw": raw}).execute()

    st.write("### Turmas encontradas:")
    st.write(turmas)

    if st.button(" Gerar e enviar planilhas"):
        remetente = "me"  # Gmail API usa 'me' como remetente autenticado
        for turma in turmas:
            st.write(f"Gerando planilha para **{turma}**...")
            arquivo_excel = gerar_excel(df_alunos, turma)

            corpo_email = (
                f"Olá, {nome_prof},\n\n"
                f"Segue em anexo a planilha de notas da turma **{turma}** "
                f"da disciplina **{disciplina}** referente à **{prova}**.\n\n"
                "Atenciosamente,\nEquipe Acadêmica."
            )

            try:
                enviar_email(
                    remetente=remetente,
                    destinatario=email_prof,
                    assunto=f"Planilha de Notas - {disciplina} - {turma} - {prova}",
                    mensagem=corpo_email,
                    arquivo=arquivo_excel,
                )
                st.success(f"E-mail enviado com sucesso para {email_prof} (Turma {turma})")
            except Exception as e:
                st.error(f"Falha ao enviar planilha da turma {turma}: {e}")
            time.sleep(1.5)  # pequeno delay para evitar rate limit

        st.success(" Todas as planilhas foram geradas e enviadas com sucesso!")
