import streamlit as st
import smtplib
import pandas as pd
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime


#st.warning("🚧 Esta página está em manutenção. Por favor, volte mais tarde.")
#st.stop()

df_base = pd.read_excel('alunos.xlsx')

def saudacao():
    hora = datetime.now().hour

    if 5 <= hora < 12:
        saudacao = "Bom dia"
    elif 12 <= hora < 18:
        saudacao = "Boa tarde"
    else:
        saudacao = "Boa noite"
    
    return saudacao

def semestres():
    
    agora = datetime.now()
    ano = str(agora.year)
    mes = agora.month
    
    if 1 <= mes <= 6:
        ano = ano+'.01'
        return
    else: 
        ano = ano+'.02'

def create_assunto(curso, disciplina, quantidade, tipo, tipo_prova, data_aplicar):

        assunto = f'Prova iCEV {disciplina} {tipo} - {quantidade} cópias'
        
        comprimento = saudacao()
        ano = semestres()
    
        mensagem = (                    
            f"{comprimento}.\n\n"
            "Solicitamos a impressão de:\n\n"
            f"Tipo: {tipo_prova}\n"
            f"Curso/Turma: {curso} {ano}\n"
            f"Disciplina: {disciplina}\n"
            f"Quantidade: {quantidade}\n\n"
            f"Data: {data_aplicar}"
        )
        
        return assunto, mensagem


def destinatarios(curso):
    emails = st.secrets["emails"]
    email_cord = st.secrets["email_cord"]

    # E-mails base (sempre vão receber)
    lista_emails = list(emails.values())

    # Adiciona coordenador específico conforme o curso
    if curso == "Bacharelado em Engenharia de Software":
        lista_emails.append(email_cord["eng"])
    elif curso == "Bacharelado em Direito":
        lista_emails.append(email_cord["dir"])
    elif curso == "Administração":
        lista_emails.append(email_cord["adm"])

    return lista_emails

    
st.title("Envio de E-mail Automático com Anexo")

# Inputs do usuário
remetente = st.text_input("Seu e-mail") # Email sistema turoria 
senha = st.text_input("Senha do e-mail", type="password") # Senha no secrets ajustar o duas etapas 


print(list(df_base.columns))

curso = df_base['CURSO'].unique().tolist()
curso = st.selectbox("Escolha o Curso", curso)

disciplinas = sorted(df_base[df_base["CURSO"] == curso]["DISCIPLINA"].unique().tolist())
disciplina = st.selectbox("Escolha a disciplina", disciplinas)

turmas_filtradas = df_base[df_base["DISCIPLINA"] == disciplina]["TURMADISC"].unique().tolist()
turma = st.selectbox("Escolha a turma", turmas_filtradas)

df_filtrado = df_base[(df_base["DISCIPLINA"] == disciplina) & (df_base["TURMADISC"] == turma)]
quantidade = (df_filtrado['ALUNO'].count()) + 5 
st.write(quantidade)


#data_aplicar = st.date_input("Selecione a data em que a prova será realizada: ")
data_aplicar = st.date_input("Selecione a data", format="DD/MM/YYYY")  # Novo parâmetro desde Streamlit 1.25
st.write("📅 Data selecionada:", data_aplicar.strftime("%d/%m/%Y"))

tipo = st.selectbox("Escolha o tipo da prova", ["Prova", "Recuperação"])
tipo_prova = "Analisando o que é isso"


assunto, mensagem = create_assunto(curso, disciplina, quantidade, tipo, tipo_prova, data_aplicar)
destinario = destinatarios(curso)


# Upload de arquivo
arquivo = st.file_uploader("Anexar arquivo", type=None)

if st.button("Enviar E-mail"):
    try:
        # Mostra os dados antes de enviar
        st.subheader("📤 Prévia do E-mail:")
        st.write("**Remetente:**", remetente)
        st.write("**Destinatário(s):**", destinario)
        st.write("**Assunto:**", assunto)
        st.write("**Mensagem:**")
        st.code(mensagem, language="markdown")
        if arquivo is not None:
            st.write("📎 **Anexo:**", arquivo.name)

        # Monta e envia
        msg = MIMEMultipart()
        msg['From'] = remetente
        msg['To'] = destinario
        msg['Subject'] = assunto
        msg.attach(MIMEText(mensagem, 'plain'))

        if arquivo is not None:
            part = MIMEApplication(arquivo.read(), Name=arquivo.name)
            part['Content-Disposition'] = f'attachment; filename="{arquivo.name}"'
            msg.attach(part)

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remetente, senha)
        server.send_message(msg)
        server.quit()

        st.success("E-mail enviado com sucesso!")

    except Exception as e:
        st.error(f"Erro ao enviar e-mail: {e}")

