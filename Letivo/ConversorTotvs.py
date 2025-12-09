
import streamlit as st
import pandas as pd
import io
import base64
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from datetime import date, datetime
import re 


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
        
        # Renomear colunas para padronizar
        df_base.rename(columns={'NOMEDISCIPLINA': 'DISCIPLINA',
                                'NOMECURSO': 'CURSO',
                                'NOMEALUNO': 'ALUNO'}, inplace=True)
        
        df.rename(columns={'NOMEDISCIPLINA': 'DISCIPLINA',
                        'NOMECURSO': 'CURSO',
                        'NOMEALUNO': 'ALUNO'}, inplace=True)

        # --- 🔍 Detectar a disciplina e filtrar df_base ---
        if 'DISCIPLINA' in df.columns and not df['DISCIPLINA'].empty:
            disciplina_arquivo = df['DISCIPLINA'].iloc[0]
            df_base = df_base[df_base['DISCIPLINA'] == disciplina_arquivo]
        else:
            st.warning("Coluna 'DISCIPLINA' não encontrada ou vazia no arquivo enviado.")
            return pd.DataFrame()
        
        # --- ✅ Garantir que só usa colunas existentes no df ---
        colunas_validas = [c for c in ['DISCIPLINA', 'RA', 'NOTAS'] if c in df.columns]
        if len(colunas_validas) < 3:
            st.warning(f"Colunas insuficientes para merge: {colunas_validas}")
            return pd.DataFrame()

        # --- 🔗 Faz o merge agora de forma segura ---
        df = pd.merge(df_base, df[colunas_validas], on=['DISCIPLINA', 'RA'], how='left')
        
        df = df.copy()
        
        # Adicionar colunas complementares
        df['CODETAPA'] = codetapa
        df['CODPROVA'] = codprova
        df['TIPOETAPA'] = tipoetapa
        df['PROVA'] = prova
        df['ETAPA'] = etapa
        df['RA novo'] = df['RA'].astype(int)
        
        # Reorganizar colunas
        colunas = ['CODCOLIGADA', 'CURSO', 'TURMADISC', 'IDTURMADISC', 'DISCIPLINA',
                'RA', 'ALUNO', 'ETAPA', 'PROVA', 'TIPOETAPA', 'CODETAPA',
                'CODPROVA', 'NOTAS']
        df = df[colunas]

        # Limpeza condicional das notas
        df_teste = df
        if prova == "Prova":
            df_teste = df_teste.dropna(subset=['NOTAS']).copy()
        elif prova in ["Recuperação", "Recuperação Final"]:
            df_teste = df_teste.dropna(subset=['NOTAS'])
            df_teste = df_teste[df_teste['NOTAS'].notna() & (df_teste['NOTAS'] != 0)]
        elif prova == "Quizz":
            df_teste = df_teste.dropna(subset=['NOTAS'])

        return df_teste

    
    def detectar_etapas_provas(df: pd.DataFrame):
        """
        Detecta automaticamente colunas que representam provas (P1, P2, P3)
        e tipos (Prova, Recuperação, Quiz). Remove colunas vazias de Quiz.
        Retorna o DataFrame limpo e um dicionário com metadados das colunas.
        """

        mapa_etapa = {"P1": 1, "P2": 2, "P3": 3}
        mapa_prova = {"PROVA": 1, "RECUPERAÇÃO": 2, "QUIZZ": 3}

        # Aceita colunas como "P1", "Quiz P1", "Rec P2", "Recuperação P3", "Prova P1"
        padrao = re.compile(r"(?:(QUIZ|QUIZZ|RECUPERAÇÃO|REC|PROVA)\s*)?(P1|P2|P3)", re.IGNORECASE)

        mapeamento = {}

        for col in df.columns:
            match = padrao.search(col)
            if match:
                tipo_raw = match.group(1).upper() if match.group(1) else "PROVA"
                etapa = match.group(2).upper()

                # Normaliza "REC" → "RECUPERAÇÃO"
                tipo_raw = tipo_raw.strip().upper()

                if tipo_raw in ["REC", "RECUPERACAO", "RECUPERAÇÃO"]:
                    tipo = "RECUPERAÇÃO"
                elif tipo_raw in ["QUIZ", "QUIZZ"]:
                    tipo = "QUIZZ"
                elif tipo_raw == "PROVA":
                    tipo = "PROVA"
                else: 
                    st.warning("COLUNA NAO RECONHECIDA")

                    
                mapeamento[col] = {
                    "etapa": etapa,
                    "prova": tipo,
                    "codetapa": mapa_etapa.get(etapa),
                    "codprova": mapa_prova.get(tipo, 1)
                }

        # === Remover colunas de QUIZ totalmente nulas ===
        colunas_quiz_vazias = [
            c for c in df.columns
            if re.search(r"QUIZ|QUIZZ", c, re.IGNORECASE) and df[c].isna().all()
        ]
        if colunas_quiz_vazias:
            df = df.drop(columns=colunas_quiz_vazias)
            st.info(f"Removidas colunas de Quiz sem dados: {', '.join(colunas_quiz_vazias)}")

        return df, mapeamento



    # Interface do Streamlit
    st.title("Conversor de Notas Totvs")

    # Upload do arquivo Excel
    uploaded_file = st.file_uploader("Envie o arquivo de notas (Excel)", type=["xlsx"])

    # Definir as variáveis de configuração para o filtro
    tipoetapa = 'N'  # Tipo de etapa
    

    if uploaded_file:
        # 1) Carrega e exibe os dados originais
        df_original = carregar_dados(uploaded_file)
        st.subheader("Dados Originais")
        df_original = df_original.dropna(axis=1, how='all') 
        df, mapeamento= detectar_etapas_provas(df_original)
        st.write(df, mapeamento)
        
        # lista para armazenar resultados por prova+disciplina
        dfs_limpos = []
        
        tipos_provas = set()
        # Loop sobre as colunas detectadas (ex: "P1", "Quiz P1", ...)
        for col, info in mapeamento.items():
            etapa = info["etapa"]
            prova_tipo = info["prova"].capitalize()   # 'Prova', 'Quiz', 'Recuperação'
            codetapa = info["codetapa"]
            codprova = info["codprova"]
            
            tipos_provas.add(prova_tipo)
            # renomeia a coluna detectada para NOTAS temporariamente
            temp = df_original.rename(columns={col: "NOTAS"})[["DISCIPLINA", "RA", "NOTAS"]].copy()

            # pega as disciplinas que existem nesse arquivo/coluna (normalmente 1)
            disciplinas_no_arquivo = temp["DISCIPLINA"].dropna().unique().tolist()
            if not disciplinas_no_arquivo:
                st.warning(f"Coluna {col}: não foi encontrada DISCIPLINA válida — pulando.")
                continue

            # itera por cada disciplina encontrada (caso o arquivo tenha mais de uma)
            for disciplina in disciplinas_no_arquivo:
                # filtra apenas as linhas da disciplina atual
                df_temp = temp[temp["DISCIPLINA"] == disciplina].copy()

                # se não houver notas válidas nessa coluna para a disciplina, pula
                if df_temp["NOTAS"].dropna().empty:
                    st.info(f"{prova_tipo} {etapa} — {disciplina}: sem notas válidas — pulando.")
                    continue
                
                if etapa == "P1" or etapa == "P2" or etapa == "P3":
                    df_temp["NOTAS"] = df_temp["NOTAS"].fillna(0)
                else: 
                    "ta de boa"

                # chama a função de limpeza (usa só DISCIPLINA, RA, NOTAS)
                df_limpo = limpar_dados(df_temp, prova_tipo, etapa, codetapa, codprova, tipoetapa)
                
                if df_limpo is None or df_limpo.empty:
                    st.info(f"{prova_tipo} {etapa} — {disciplina}: nenhum registro após limpeza.")
                    continue

                dfs_limpos.append({
                    "disciplina": disciplina,
                    "prova": prova_tipo,
                    "etapa": etapa,
                    "codetapa": codetapa,
                    "codprova": codprova,
                    "df": df_limpo
                })

                st.success(f"{prova_tipo} {etapa} — {disciplina}: processada ({len(df_limpo)} registros).")

        # concatena todos os dataframes processados (se houver)
        if not dfs_limpos:
            st.warning("Nenhuma coluna de prova válida encontrada após filtro por disciplina.")
            st.stop()

        df_final = pd.concat([item["df"] for item in dfs_limpos], ignore_index=True)
        st.subheader("Dados combinados de todas as provas (após filtro por disciplina)")
        st.dataframe(df_final)
        
        df_limpo = df_final.copy()

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
        
    
        tipos_provas = "_".join(sorted(tipos_provas))
        name_file = f"{disciplina}_{turma}_{tipos_provas}_{etapa}.txt"
        
        clicou = st.download_button(
            label="Baixar Notas Tratadas (TXT)",
            data=output,
            file_name=name_file,
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
            pasta_prova_id      = encontrar_ou_criar_pasta(prova_tipo, pasta_disciplina_id)

            now = datetime.now().strftime('%Y-%m-%d %H:%M')
            nome_xlsx = f"{disciplina}_{turma}_{prova_tipo}_{etapa}_{now}.xlsx"

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
