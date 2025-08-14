import streamlit as st
import pandas as pd
import io
import math 
import base64
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from datetime import date


def carregar():
    
    df = st.session_state["dados"].get("alunosxdisciplinas")
    df_totvs = df.copy()    
    df_disciplina = st.session_state["dados"].get("disciplina")

    def arrendondar_para_cima(numero, decimal):
        fator = 10 ** decimal
        return math.ceil(numero * fator) / fator

    def organizar(df):
        # Substituir "-" por 0
        df.replace("-", 0, inplace=True)
        df = df.infer_objects(copy=False)

        # Converter colunas para número onde for possível
        for col in df.columns:
            try:
                df[col] = pd.to_numeric(df[col])
            except ValueError:
                pass  # Mantém colunas não numéricas inalteradas

        # Remover colunas que possuem apenas zeros
        df = df.loc[:, (df != 0).any(axis=0)]
        return df

    # Função para carregar o arquivo
    @st.cache_data
    def carregar_dados(arquivo):
        try:
            # Tenta carregar como arquivo Excel
            df = pd.read_excel(arquivo)
            return df
        except Exception as e:
            try:
                # Se falhar, tenta carregar como arquivo TXT (tabulado)
                df = pd.read_csv(arquivo, delimiter=",")
                return df
            except Exception as e:
                st.error(f"Erro ao carregar o arquivo: {e}")
                return pd.DataFrame()

    # Função para limpar os dados
    @st.cache_data
    def limpar_dados(df, prova, etapa, codetapa, codprova, tipoetapa):
        df_alunos = st.session_state["dados"].get("alunosxdisciplinas")
        df_base = df_alunos.copy()
        
        df['Nomes'] = df['Nome'] + ' ' + df['Sobrenome']
        
        # Selecionando as notas dos quizzes
        notas = df.filter(regex='Questionário:')
        remocao_cols = notas.filter(regex='Remoção')
        notas = notas.drop(columns=remocao_cols)
        
        # Converter todas as colunas selecionadas para o tipo numérico
        notas = notas.apply(pd.to_numeric, errors='coerce', downcast='integer').fillna(0)
        
        # Calcular a média das 75% melhores notas de cada aluno
        media = notas.apply(lambda x: x.nlargest(int(len(x)*0.75)).mean(), axis=1)

        
        # Calcular média final de cada aluno
        df = df.assign(media=media)
        df['Media_Final'] = df['media'].apply(lambda x: round(x * 0.2, 2))

        # Imprimir a tabela com nomes e notas
        colunas = ['Nomes', 'Media_Final']
        media_final = df.loc[:, colunas]
        media_final = media_final.sort_values(by='Nomes')
        #print(media_final)

        df['Media_Final'] = df['Media_Final'].apply(lambda x: arrendondar_para_cima(x, 1))
        
        # Imprimir a tabela com nomes e notas
        colunas = ['Número de identificação','Nomes', 'Media_Final']
        df_arredondamento = df.loc[:, colunas]
        df_arredondamento = df_arredondamento.sort_values(by='Nomes')
            
        #Ajustes
        df_arredondamento.rename(columns={'Número de identificação': 'RA',
                                        'Media_Final': 'NOTAS',
                                        'Nomes': 'ALUNO'}, inplace=True)
        df_arredondamento['DISCIPLINA'] = disciplina
        df_arredondamento['TURMADISC'] = turma
        df_arredondamento['RA'] = df_arredondamento['RA'].apply(lambda x: f"{x:0>7}")
        df = df_arredondamento    
        
        df_base['RA'] = df_base['RA'].apply(lambda x: str(x).zfill(7))
        df['RA'] = df['RA'].apply(lambda x: str(x).zfill(7))
        
        colunas=['RA', 'ALUNO', 'TURMADISC', 'DISCIPLINA', 'NOTAS']
        df = df[colunas]

        # Renomear colunas
        df_base.rename(columns={'NOMEDISCIPLINA': 'DISCIPLINA',
                                'NOMECURSO': 'CURSO',
                                'NOMEALUNO': 'ALUNO'}, inplace=True)
        
        df = pd.merge(df_base, df[['DISCIPLINA', 'RA', 'NOTAS']],
                    on=['DISCIPLINA', 'RA' ],
                    how='left')    
            
        # Adicionar as novas colunas
        df['CODETAPA'] = codetapa
        df['CODPROVA'] = codprova
        df['TIPOETAPA'] = tipoetapa
        df['PROVA'] = prova
        df['ETAPA'] = etapa
    
        
        # Nova ordem das colunas
        colunas = ['CODCOLIGADA', 'CURSO', 'TURMADISC', 'IDTURMADISC', 'DISCIPLINA', 'RA', 'ALUNO', 'ETAPA', 'PROVA', 'TIPOETAPA', 'CODETAPA', 'CODPROVA', 'NOTAS']
        df_limpo = df[colunas]
        
        df_limpo = df_limpo[(df_limpo['DISCIPLINA'] == disciplina) & (df_limpo['TURMADISC'] == turma)].copy()

        return df_limpo
    
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

    # Interface do Streamlit
    st.title("Limpeza e Tratamento de Notas Quizzes")

    # Definir as variáveis de configuração para o filtro
    etapa = st.selectbox('Selecione a etapa', ['P1', 'P2'])
    prova = "Quizz"
    tipoetapa = 'N'  # Tipo de etapa
    codetapa = 1  # Código da etapa
    codprova = 3  # Código da prova

    # Limitar as opções de Etapa com base na escolha da Prova
    if etapa == 'P1':
        codetapa = 1
    elif etapa == 'P2':
        codetapa = 2   
        
    curso = df_totvs['CURSO'].unique().tolist()
    curso = st.selectbox("Escolha o Curso", curso)

    disciplinas = sorted(df_totvs[df_totvs["CURSO"] == curso]["DISCIPLINA"].unique().tolist())
    disciplina = st.selectbox("Escolha a disciplina", disciplinas)

    turmas_filtradas = df_totvs[df_totvs["DISCIPLINA"] == disciplina]["TURMADISC"].unique().tolist()
    turma = st.selectbox("Escolha a turma", turmas_filtradas)


    # Upload do arquivo Excel
    uploaded_file = st.file_uploader("Envie o arquivo de notas (Excel)", type=["xlsx"])

    codigo_disciplina = df_totvs[(df_totvs["DISCIPLINA"] == disciplina) & (df_totvs["TURMADISC"] == turma)]["IDTURMADISC"].unique().tolist()
    st.write(f"ID da disciplina: **{codigo_disciplina}**")

    df_curso = pd.DataFrame(df_disciplina)

    df_curso = df_curso[['NOME', 'IDMOODLE', 'CODTURMA']]

    codigo_disciplina = df_curso[(df_curso["NOME"] == disciplina) & (df_curso['CODTURMA'] == turma)]["IDMOODLE"].tolist()
    codturma = df_curso[(df_curso["NOME"] == disciplina) & (df_curso['CODTURMA'] == turma)]["CODTURMA"].tolist()
    st.write(f"ID da disciplina: **{codigo_disciplina}**, Turma: **{codturma}**")
    if codturma:
        st.write(f"Link para Quiz \nhttp://icev.digital/grade/export/xls/index.php?id={codigo_disciplina[0]}")
        st.write(f"Link para Abado Curso \nhttps://moodle.icev.digital/course/view.php?id={codigo_disciplina[0]}")
        
    else: 
        st.write(f"CODTURMA VAZIO")
            
    st.subheader("Documento gerado para saber id do icev")
    st.dataframe(df_curso)

    # Carregar e limpar os dados
    if uploaded_file:
        df_original = carregar_dados(uploaded_file)
        st.subheader("Dados Originais")
        
        df_original = organizar(df_original)
        st.dataframe(df_original)
        
        # Limpar dados
        df_limpo = limpar_dados(df_original, prova, etapa, codetapa, codprova, tipoetapa)
        st.subheader("Dados Após Limpeza")
        df_limpo = df_limpo[(df_limpo['DISCIPLINA'] == disciplina) & (df_limpo['TURMADISC'] == turma)].copy()
        
        remover_zeros = st.checkbox("Remover alunos com nota 0", value=False)
        if remover_zeros:
            df_limpo = df_limpo[df_limpo['NOTAS'] != 0]
        
        st.dataframe(df_limpo)
        
        disciplina = df_limpo['DISCIPLINA'].iloc[0]
        turma = df_limpo['TURMADISC'].iloc[0]
        
        df_limpo['RA'] = df_limpo['RA'].astype(str)
        df_limpo['RA'] = df_limpo['RA'].apply(lambda x: str(x).zfill(7))
        df_limpo['NOTAS'] = pd.to_numeric(df_limpo['NOTAS'], errors='coerce')
        df_limpo['NOTAS'] = df_limpo['NOTAS'].apply(lambda x: f"{x:.2f}".replace('.', ','))
        
        # Criar o arquivo .txt com separador ';'
        output = io.BytesIO()  
        df_limpo.to_csv(output, index=False, sep=';', encoding='utf-8', header=False)
        output.seek(0) 
        
        if remover_zeros:
            nome_arquivo=f"{disciplina}_{turma}_{prova}_{etapa}_REMOTO.txt"
        else: 
            nome_arquivo=f"{disciplina}_{turma}_{prova}_{etapa}.txt"
        
        # Botão para baixar o arquivo tratado como .txt
        clicou = st.download_button(
            label="⬇ Baixar Notas Tratadas (TXT)",
            data=output,
            file_name=nome_arquivo,
            mime="text/plain"
        )
        
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
            df_limpo.to_excel(writer, index=False, sheet_name="Notas")
        excel_buffer.seek(0)

        if clicou:
            pasta_curso_id      = encontrar_ou_criar_pasta(curso, pasta_raiz_id)
            pasta_disciplina_id = encontrar_ou_criar_pasta(disciplina, pasta_curso_id)
            pasta_turma_id      = encontrar_ou_criar_pasta(turma, pasta_disciplina_id)
            pasta_prova_id      = encontrar_ou_criar_pasta(prova, pasta_turma_id)

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
