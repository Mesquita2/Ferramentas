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

def create_assunto(curso, disciplina, quantidade, tipo, tipo_prova):

        assunto = f'Prova iCEV {disciplina} {tipo} - {quantidade} cópias'
        
        comprimento = saudacao()
        ano = semestres()
        
        mensagem = f'''
            {comprimento}. 

            Solicitamos a impressão de:

            Tipo: {tipo_prova} 
            Curso/Turma: {curso} {ano}
            Disciplina: {disciplina}
            Quantidade: {quantidade}

            Data: {data_aplicar}
        '''
        
        return assunto, mensagem


st.title("Envio de E-mail Automático com Anexo")

# Inputs do usuário
remetente = st.text_input("Seu e-mail") # Email sistema turoria 
senha = st.text_input("Senha do e-mail", type="password") # Senha no secrets ajustar o duas etapas 
destinatario = st.text_input("Destinatário")

print(list(df_base.columns))

cursos = df_base["NOMECURSO"].unique().tolist()
curso = st.selectbox("Escolha o Bacharelado")

disciplinas = df_base["DISCIPLINA"].unique().tolist()
disciplina = st.selectbox("Escolha a disciplina", disciplinas)

turmas_filtradas = df_base[df_base["DISCIPLINA"] == disciplina]["TURMADISC"].unique().tolist()
turma = st.selectbox("Escolha a turma", turmas_filtradas)

df_filtrado = df_base[(df_base["DISCIPLINA"] == disciplina) & (df_base["TURMADISC"] == turma)]
quantidade = (df_filtrado['ALUNO'].count()) + 5 


data_aplicar = st.date_input("Selecione a data em que a prova será realizada: ")
tipo = st.selectbox("Escolha o tipo da prova", ["Prova", "Recuperação"])
tipo_prova = "Analisando o que é isso"


assunto, mensagem = create_assunto(curso, disciplina, quantidade, tipo, tipo_prova, data_aplicar)

# Upload de arquivo
arquivo = st.file_uploader("Anexar arquivo", type=None)

if st.button("Enviar E-mail"):
    try:
        # Montando o e-mail
        msg = MIMEMultipart()
        msg['From'] = remetente
        msg['To'] = destinatario
        msg['Subject'] = assunto
        msg.attach(MIMEText(mensagem, 'plain'))
        
        if arquivo is not None:
            part = MIMEApplication(arquivo.read(), Name=arquivo.name)
            part['Content-Disposition'] = f'attachment; filename="{arquivo.name}"'
            msg.attach(part)

        # Enviar via SMTP
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remetente, senha)
        server.send_message(msg)
        server.quit()

        st.success("E-mail enviado com sucesso!")
    except Exception as e:
        st.error(f"Erro ao enviar e-mail: {e}")
