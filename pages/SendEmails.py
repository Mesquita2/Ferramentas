import smtplib
import streamlit as st
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from auth import check_authentication
import pandas as pd 

if not check_authentication():
    st.stop()
    
# Função para carregar os alunos do arquivo Excel
def carregar_alunos():
    try:
        df = pd.read_excel("alunos.xlsx", dtype={"RA": str})
        df.rename(columns={'NOMEDISCIPLINA': 'DISCIPLINA',
                           'NOMECURSO': 'CURSO',
                           'NOMEALUNO': 'ALUNO',
                           'TURMADISC': 'TURMADISC'}, inplace=True)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo alunos.xlsx: {e}")
        return pd.DataFrame()

st.title("Escolher disciplina para enviar para mecanografia")

df_alunos = carregar_alunos()
if df_alunos.empty:
    st.stop()

disciplinas = df_alunos["DISCIPLINA"].unique().tolist()
disciplina = st.selectbox("📖 Escolha a disciplina", disciplinas)

turmas_filtradas = df_alunos[df_alunos["DISCIPLINA"] == disciplina]["TURMADISC"].unique().tolist()
turma = st.selectbox("🏫 Escolha a turma", turmas_filtradas)

prova = st.selectbox("Escolha se é P1 ou P2", ["P1", "P2"])

df_filtrado = df_alunos[(df_alunos["DISCIPLINA"] == disciplina) & (df_alunos["TURMADISC"] == turma)]
num_alunos = df_alunos[(df_alunos["DISCIPLINA"] == disciplina) & (df_alunos["TURMADISC"] == turma)]["RA"].nunique()

st.write(f"📝 **Alunos da Disciplina: {disciplina} | Turma: {turma}** (Total: {num_alunos} alunos)")


destinatario = st.text_input("📩 E-mail do destinatário", "")

# Gerar um arquivo de exemplo (simulação do anexo)
df_example = "RA;ALUNO;NOTAS\n1001;João Silva;9.0\n1002;Maria Oliveira;8.5"
arquivo = io.BytesIO(df_example.encode('utf-8'))
arquivo.name = f"{disciplina}_{turma}.txt"

# Botão para enviar e-mail
if st.button("📤 Enviar E-mail"):
    if not destinatario:
        st.error("❌ Por favor, insira um e-mail válido.")
    else:
        try:
            # Criar e-mail
            msg = MIMEMultipart()
            msg["From"] = remetente
            msg["To"] = destinatario
            msg["Subject"] = f"Notas da Disciplina {disciplina} - Turma {turma}"

            # Corpo do e-mail
            mensagem = f"Olá,\n\nSegue anexo o arquivo de notas da disciplina {disciplina}, turma {turma}, com {num_alunos} alunos.\n\nAtenciosamente."
            msg.attach(MIMEText(mensagem, "plain"))

            # Adicionar anexo
            anexo = MIMEBase("application", "octet-stream")
            anexo.set_payload(arquivo.getvalue())
            encoders.encode_base64(anexo)
            anexo.add_header("Content-Disposition", f"attachment; filename={arquivo.name}")
            msg.attach(anexo)

            # Conectar ao servidor SMTP e enviar
            with smtplib.SMTP("smtp.gmail.com", 587) as servidor:
                servidor.starttls()
                servidor.login(remetente, senha)
                servidor.sendmail(remetente, destinatario, msg.as_string())

            st.success(f"✅ E-mail enviado com sucesso para {destinatario}!")

        except Exception as e:
            st.error(f"❌ Erro ao enviar e-mail: {e}")
