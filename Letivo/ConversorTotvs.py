
import streamlit as st
import pandas as pd
import io
import base64
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from datetime import date


def carregar():
    # Função para carregar o arquivo
    token_b64 = st.secrets["gmail_token"]["token_b64"]

    pasta_raiz_id = st.secrets["drive_pasta_notas"]["drive_notas"]

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
    
    @st.cache_data
    def carregar_dados(arquivo):
        try:
            df = pd.read_excel(arquivo)
            return df
        except Exception as e:
            st.error(f"Erro ao carregar o arquivo: {e}")
            return pd.DataFrame()

    # Função para limpar os dados
    @st.cache_data
    def limpar_dados(df, prova, etapa, codetapa, codprova, tipoetapa):
        df_aluno = st.session_state["dados"].get("alunosxdisciplinas")
        df_base = df_aluno.copy()
        
        

        df_base['RA'] = df_base['RA'].astype(str).str.zfill(7)
        df['RA'] = df['RA'].astype(str).str.zfill(7)
        
        # Renomear colunas
        df_base.rename(columns={'NOMEDISCIPLINA': 'DISCIPLINA',
                                'NOMECURSO': 'CURSO',
                                'NOMEALUNO': 'ALUNO'}, inplace=True)
        
        df.rename(columns={'NOMEDISCIPLINA': 'DISCIPLINA',
                        'NOMECURSO': 'CURSO',
                        'NOMEALUNO': 'ALUNO'}, inplace=True)

        
        df = pd.merge(df_base, df[['DISCIPLINA', 'RA',  'NOTAS']],
                    on=['DISCIPLINA', 'RA'],
                    how='left')  
        
        df = df.copy()
        
        # Adicionar as novas colunas
        df['CODETAPA'] = codetapa
        df['CODPROVA'] = codprova
        df['TIPOETAPA'] = tipoetapa
        df['PROVA'] = prova
        df['ETAPA'] = etapa
        df['RA novo'] = df['RA'].astype(int)
        
        # Nova ordem das colunas
        colunas = ['CODCOLIGADA', 'CURSO', 'TURMADISC', 'IDTURMADISC', 'DISCIPLINA', 'RA', 'ALUNO', 'ETAPA', 'PROVA', 'TIPOETAPA', 'CODETAPA', 'CODPROVA', 'NOTAS']
        df = df[colunas]

        # Condicional para a limpeza das notas
        df_teste = df
        if prova == "Prova":
            df_teste = df_teste.dropna(subset=['NOTAS']).copy()
        elif prova == "Recuperação" or prova == "Recuperação Final":
            df_teste = df_teste.dropna(subset=['NOTAS'])
            df_teste = df_teste[df_teste['NOTAS'] != 0]
        elif prova == "Quizz":
            df_teste = df_teste.dropna(subset=['NOTAS'])


        return df_teste

    # Interface do Streamlit
    st.title("Conversor de Notas Totvs")

    # Upload do arquivo Excel
    uploaded_file = st.file_uploader("Envie o arquivo de notas (Excel)", type=["xlsx"])

    # Definir as variáveis de configuração para o filtro
    etapa = st.selectbox('Selecione a etapa', ['P1', 'P2', 'P3', 'REC FINAL'])
    prova = st.selectbox('Selecione o tipo de prova', ['Prova', 'Recuperação', 'Quizz', 'Recuperação Final'])
    tipoetapa = 'N'  # Tipo de etapa
    codetapa = 2  # Código da etapa
    codprova = 1  # Código da prova

    # Limitar as opções de Etapa com base na escolha da Prova
    if etapa == 'P1' and prova == "Prova":
        codetapa = 1  # P1 = 1
        codprova = 1  # Prova = 1
    elif etapa == 'P2' and prova == "Prova":
        codetapa = 2  # P2 = 2
        codprova = 1  # Prova = 1
    elif etapa == 'P1' and prova == "Recuperação":
        codetapa = 1  # P1 = 1
        codprova = 2  # Recuperação = 2
    elif etapa == 'P2' and prova == "Recuperação":
        codetapa = 2  # P2 = 2
        codprova = 2  # Recuperação = 2
    elif etapa == 'P1' and prova == 'Quizz': 
        codetapa = 1
        codprova = 3
    elif etapa == 'P2' and prova == 'Quizz':
        codetapa = 2
        codprova = 3 
    elif etapa == 'P3' and prova == "Prova":
        codetapa = 3
        codprova = 1
    elif etapa == 'REC FINAL' and prova == "Recuperação Final":
        codetapa = 5
        codprova = 1 

    if uploaded_file:
        # 1) Carrega e exibe os dados originais
        df_original = carregar_dados(uploaded_file)
        st.subheader("Dados Originais")
        st.dataframe(df_original)

        # 2) Limpa e formata
        df_limpo = limpar_dados(df_original, prova, etapa, codetapa, codprova, tipoetapa)
        st.subheader("Dados Após Limpeza")
        st.dataframe(df_limpo)

        df_limpo['RA']    = df_limpo['RA'].astype(str).str.zfill(7)
        df_limpo['NOTAS']= pd.to_numeric(df_limpo['NOTAS'], errors='coerce')
        if (df_limpo['NOTAS'] > 8).any():
            st.info("Existem alunos com nota maior que 8.")

        # 3) Gera e oferece o download do TXT
        output = io.BytesIO()
        df_limpo['NOTAS'] = df_limpo['NOTAS']\
            .apply(lambda x: f"{x:.2f}".replace('.', ',') if isinstance(x, (int, float)) else x)
        df_limpo.to_csv(output, index=False, sep=';', header=False, encoding='utf-8')
        output.seek(0)
        
        # Extrai disciplina, turma e curso do DataFrame original
        disciplina = df_limpo['DISCIPLINA'].iloc[0]
        turma = df_limpo['TURMADISC'].iloc[0]
        curso = df_limpo['CURSO'].iloc[0] 

        clicou = st.download_button(
            label="Baixar Notas Tratadas (TXT)",
            data=output,
            file_name=f"{disciplina}_{turma}_{prova}_{etapa}.txt",
            mime="text/plain"
        )

        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
            df_limpo.to_excel(writer, index=False, sheet_name="Notas")
        excel_buffer.seek(0)

        if clicou:
            pasta_curso_id      = encontrar_ou_criar_pasta(curso, pasta_raiz_id)
            pasta_turma_id      = encontrar_ou_criar_pasta(turma, pasta_curso_id)
            pasta_disciplina_id = encontrar_ou_criar_pasta(disciplina, pasta_turma_id)
            pasta_prova_id      = encontrar_ou_criar_pasta(prova, pasta_disciplina_id)

            now = date.today().strftime('%Y-%m-%d')
            nome_xlsx = f"{disciplina}_{turma}_{prova}_{etapa}_{now}.xlsx"

            media = MediaIoBaseUpload(
                excel_buffer,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            metadata = {"name": nome_xlsx, "parents": [pasta_prova_id]}

            drive_service.files().create(
                body=metadata,
                media_body=media,
                fields="id,name"
            ).execute()

            st.success(f"Arquivo Excel salvo no Drive: {nome_xlsx}")
