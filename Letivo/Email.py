import streamlit as st
import pandas as pd
import base64
import io 
import time
from datetime import date, datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.discovery import build
import openpyxl
import pickle


def carregar():
    
    token_b64 = st.secrets["gmail_token"]["token_b64"]

    with open("token_gmail.pkl", "wb") as token_file:
        token_file.write(base64.b64decode(token_b64))

    with open("token_gmail.pkl", "rb") as token:
        creds = pickle.load(token)

    drive_service = build("drive", "v3", credentials=creds)

    SCOPES = [
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/drive.file", 
        "https://www.googleapis.com/auth/drive.metadata",  
    ]

    @st.cache_resource(show_spinner=False)
    def criar_servico_gmail():
        return build("gmail", "v1", credentials=creds)

    # --- Início do seu código ---
    if "dados" not in st.session_state:
        st.session_state["dados"] = {"alunosxdisciplinas": pd.DataFrame()}

    df_alunos = st.session_state["dados"].get("alunosxdisciplinas", pd.DataFrame())
    df_base = df_alunos.copy()

    def saudacao():
        h = datetime.now().hour
        return "Bom dia" if h<12 else "Boa tarde" if h<18 else "Boa noite"

    def semestres(dt):
        return f"{dt.year}.01" if dt.month<=6 else f"{dt.year}.02"

    def create_assunto(curso, disciplina, quantidade, tipo, tipo_prova, data_aplicar, turma):
        assunto = f'Prova iCEV {disciplina} - {tipo} - {quantidade} cópias, Turma: {turma}'
        msg = (
            f"{saudacao()}.\n\n"
            "Solicitamos a impressão de:\n\n"
            f"Tipo: {tipo_prova}\n"
            f"Curso/Turma: {curso} {semestres(data_aplicar)} {turma}\n"
            f"Disciplina: {disciplina}\n"
            f"Quantidade: {quantidade} cópias\n\n"
            f"Data: {data_aplicar.strftime('%d/%m/%Y')}"
        )
        return assunto, msg

    def destinatarios(curso):
        base = list(st.secrets["emails"].values())
        cord = st.secrets["email_cord"]
        m = {"Engenharia de Software": cord.get("eng"),
            "Direito": cord.get("dir"),
            "Administração de Empresas": cord.get("adm")}
        e = m.get(curso.strip())
        return base + ([e] if e else [])

    def enviar_email_gmail_api(remetente, destinatarios, assunto, mensagem, arquivo=None, tentativas=3, espera=2):
        service = criar_servico_gmail()

        for tentativa in range(1, tentativas + 1):
            try:
                msg = MIMEMultipart()
                msg["From"] = remetente
                msg["To"] = ", ".join(destinatarios)
                msg["Subject"] = assunto
                msg.attach(MIMEText(mensagem, "plain"))
                if arquivo:
                    arquivo.seek(0)
                    part = MIMEApplication(arquivo.read(), Name=arquivo.name)
                    part["Content-Disposition"] = f'attachment; filename="{arquivo.name}"'
                    msg.attach(part)
                raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
                service.users().messages().send(userId="me", body={"raw": raw}).execute()
                return True  
            except Exception as e:
                print(f"Tentativa {tentativa} falhou: {e}")
                if tentativa < tentativas:
                    time.sleep(espera)
                else:
                    return False 

    def encontrar_ou_criar_pasta(nome, id_pasta_mae):
        """
        Verifica se a pasta já existe dentro da pasta mãe. Se não existir, cria.
        Retorna o ID da pasta.
        """
        query = f"'{id_pasta_mae}' in parents and name = '{nome}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        resultados = drive_service.files().list(q=query, fields="files(id, name)").execute()
        arquivos = resultados.get("files", [])

        if arquivos:
            return arquivos[0]["id"]
        else:
            # Cria a pasta
            metadata = {
                "name": nome,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [id_pasta_mae],
            }
            pasta = drive_service.files().create(body=metadata, fields="id").execute()
            return pasta["id"]

    def salvar_arquivo_em_pasta(uploaded_file, nome_arquivo, curso, turma, pasta_raiz_id, tipodeprova):
        pasta_curso_id = encontrar_ou_criar_pasta(curso, pasta_raiz_id)
        pasta_turma_id = encontrar_ou_criar_pasta(turma, pasta_curso_id)
        pasta_tipo_id = encontrar_ou_criar_pasta(tipodeprova, pasta_turma_id)
        media = MediaIoBaseUpload(uploaded_file, mimetype=uploaded_file.type)

        metadata = {
            "name": nome_arquivo,
            "parents": [pasta_tipo_id],
        }

        arquivo = drive_service.files().create(
            body=metadata,
            media_body=media,
            fields="id, name"
        ).execute()

        return arquivo["id"], arquivo["name"]
    
    # Calcular dias prazo minimo 
    def calcular_dias_uteis(data_inicio, data_fim):
        dias = pd.bdate_range(data_inicio, data_fim)  # bdate_range ignora sábados e domingos
        return len(dias) - 1  # exclui o próprio dia_inicio

    # --- Interface Streamlit ---
    st.title("Envio de Provas por E-mail (Gmail API)")

    remetente = st.secrets["email_sis"]["sistema"]

    # CURSO
    cursos = sorted(df_base['CURSO'].dropna().unique())
    curso = st.selectbox("Curso", ["Selecione..."] + list(cursos))

    if curso != "Selecione...":
        disciplinas = sorted(df_base[df_base["CURSO"] == curso]["DISCIPLINA"].dropna().unique())
        disciplina = st.selectbox("Disciplina", ["Selecione..."] + list(disciplinas))

        if disciplina != "Selecione...":
            turmas = sorted(df_base[df_base["DISCIPLINA"] == disciplina]["TURMADISC"].dropna().unique())
            turmas_selecionadas = st.multiselect("Turmas", turmas)

            if turmas_selecionadas:
                quantidade_total = (
                    df_base[(df_base["DISCIPLINA"] == disciplina) & 
                            (df_base["TURMADISC"].isin(turmas_selecionadas))]['ALUNO'].count() + (5 * len(turmas_selecionadas))
                )

                st.markdown(f"**Quantidade de cópias (total):** {quantidade_total}")

                
                data_aplicar = st.date_input("Data da prova")
                
                # Entrada de data
                data_aplicar = st.date_input("Data da prova", min_value=date.today())

                # Calcula dias úteis entre hoje e a data escolhida
                dias_uteis = calcular_dias_uteis(date.today(), data_aplicar)

                if dias_uteis < 3:
                    st.error(f"ATENÇÃO: Prazo mínimo de 3 dias úteis para impressão. Faltam apenas {dias_uteis} dias úteis.")
                else:
                    st.success(f"Prazo atendido: {dias_uteis} dias úteis até a data escolhida.")
                    st.stop()

                
                tipo = st.selectbox("Tipo", ["Prova", "Recuperação", "Prova final"])
                if tipo == "Recuperação":
                    ##quantidade_total= print("Quantidade de cópias (total) baseado nas notas menor que 7 (prova + quizz)")
                    pasta_raiz = st.secrets["drive_pasta_recuperacao"]["drive_recuperacao"]
                else: 
                    pasta_raiz = st.secrets["drive_pasta"]["drive_provas"]
                tipo_prova = st.selectbox("Nº Prova", ["1", "2"])

                tipodeprova = tipo + " " + tipo_prova
                
                dest_list = destinatarios(curso)
                arquivo = st.file_uploader("Anexo (opcional)")

                if st.button("Enviar"):
                    if not arquivo:
                        st.warning("Por favor, envie um arquivo antes de continuar.")
                        st.stop()
                    try:
                        st.subheader("Prévia:")
                        st.write("De:", remetente)
                        st.write("Para:", dest_list)

                        assunto_preview, mensagem_preview = create_assunto(
                            curso, disciplina, quantidade_total, tipo, tipo_prova, data_aplicar, ", ".join(turmas_selecionadas)
                        )

                        st.write("Assunto:", assunto_preview)
                        st.code(mensagem_preview, language="markdown")

                        if arquivo:
                            st.write("Anexo:", arquivo.name)

                        erros = []
                        for turma in turmas_selecionadas:
                            assunto, mensagem = create_assunto(
                                curso, disciplina,
                                df_base[(df_base["DISCIPLINA"] == disciplina) & (df_base["TURMADISC"] == turma)]['ALUNO'].count() + 5,
                                tipo, tipo_prova, data_aplicar, turma
                            )

                            if arquivo:
                                id_salvo, nome_salvo = salvar_arquivo_em_pasta(
                                    uploaded_file=arquivo,
                                    nome_arquivo=arquivo.name,
                                    curso=curso,
                                    turma=turma,
                                    pasta_raiz_id=pasta_raiz,
                                    tipodeprova=tipodeprova
                                )
                                st.success(f"Arquivo salvo no Drive ({turma}): {nome_salvo}")

                            sucesso = enviar_email_gmail_api(remetente, dest_list, assunto, mensagem, arquivo)
                            # Enviar email para o professor que a prova foi enviada para mecanografia
                            if sucesso:
                                st.success(f"E-mail enviado para turma {turma}")
                            else:
                                erros.append(turma)
                        
                        if erros:
                            st.error(f"Erro ao enviar para as turmas: {', '.join(erros)}")
                        
                    except Exception as e:
                        st.error(f"Erro inesperado: {e}")
                
                        
