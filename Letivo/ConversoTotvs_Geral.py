import streamlit as st
import pandas as pd
import io
import re

def carregar():
    st.title("Conversor de Notas Totvs")
    st.write("Em Manutenção...")
    st.stop()

    # Função para carregar o arquivo
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

        # Detectar a disciplina no arquivo enviado
        disciplina_arquivo = df['DISCIPLINA'].iloc[0]

        # Filtrar o df_base para manter apenas a disciplina do arquivo
        df_base = df_base[df_base['DISCIPLINA'] == disciplina_arquivo]

        # Detectar automaticamente a coluna de notas
        nome_esperado = f"NOTAS {etapa.upper()}"
        colunas_compatíveis = [col for col in df.columns if nome_esperado in col.upper()]

        if not colunas_compatíveis:
            st.warning(f"Coluna correspondente a '{nome_esperado}' não encontrada.")
            return pd.DataFrame()

        coluna_nota = colunas_compatíveis[0]
        df.rename(columns={coluna_nota: 'NOTAS'}, inplace=True)

        # Merge com base de alunos
        df = pd.merge(df_base, df[['DISCIPLINA', 'RA', 'NOTAS']],
                    on=['DISCIPLINA', 'RA'],
                    how='left')

        # Adiciona metadados e trata notas
        df['CODETAPA'] = codetapa
        df['CODPROVA'] = codprova
        df['TIPOETAPA'] = tipoetapa
        df['PROVA'] = prova
        df['ETAPA'] = etapa
        df['RA novo'] = df['RA'].astype(int)
        df['NOTAS'] = pd.to_numeric(df['NOTAS'], errors='coerce').fillna(0)

        # Reorganiza colunas
        colunas_finais = ['CODCOLIGADA', 'CURSO', 'TURMADISC', 'IDTURMADISC', 'DISCIPLINA', 'RA', 'ALUNO',
                        'ETAPA', 'PROVA', 'TIPOETAPA', 'CODETAPA', 'CODPROVA', 'NOTAS']
        df = df[colunas_finais]

        return df

    # === FUNÇÃO: detectar e limpar colunas ===
    def detectar_etapas_provas(df: pd.DataFrame):
        """
        Detecta automaticamente colunas que representam provas (P1, P2, P3)
        e tipos (Prova, Recuperação, Quizz). Remove colunas vazias de Quiz.
        Retorna o DataFrame limpo e um dicionário com metadados das colunas.
        """

        # Mapas de códigos
        mapa_etapa = {"P1": 1, "P2": 2, "P3": 3}
        mapa_prova = {"PROVA": 1, "RECUPERAÇÃO": 2, "QUIZ": 3, "QUIZZ": 3}

        padrao = re.compile(r"(QUIZ|QUIZZ|RECUPERAÇÃO|PROVA).*?(P1|P2|P3)", re.IGNORECASE)

        mapeamento = {}

        for col in df.columns:
            match = padrao.search(col)
            if match:
                tipo = match.group(1).upper()
                etapa = match.group(2).upper()

                # Salva metadados da coluna
                mapeamento[col] = {
                    "etapa": etapa,
                    "prova": tipo,
                    "codetapa": mapa_etapa.get(etapa),
                    "codprova": mapa_prova.get(tipo)
                }

        # === Remover colunas de QUIZ totalmente nulas ===
        colunas_quiz_vazias = [
            c for c in df.columns if re.search(r"QUIZ|QUIZZ", c, re.IGNORECASE) and df[c].isna().all()
        ]
        if colunas_quiz_vazias:
            df = df.drop(columns=colunas_quiz_vazias)
            st.info(f"Removidas colunas de Quiz sem dados: {', '.join(colunas_quiz_vazias)}")

        return df, mapeamento
    # Interface do Streamlit
    st.title("Limpeza e Tratamento de Notas")

    # Upload do arquivo Excel
    uploaded_file = st.file_uploader("Envie o arquivo de notas (Excel)", type=["xlsx"])

    # Definir as variáveis de configuração para o filtro
    tipoetapa = 'N'  # Tipo de etapa
    df, mapeamento= detectar_etapas_provas(uploaded_file)
    st.write(df, mapeamento)
    
    
    
    # Carregar e limpar os dados
    if uploaded_file:
        df_original = carregar_dados(uploaded_file)
        st.subheader("Dados Originais")
        st.dataframe(df_original)
        
        disciplina = df_original['DISCIPLINA'].iloc[0]
        turma = df_original['TURMADISC'].iloc[0]
        
        # Limpar dados
        df_limpo = limpar_dados(df_original, prova, etapa, codetapa, codprova, tipoetapa)
        
        
        
        output = io.BytesIO()  
        df_limpo['NOTAS'] = df_limpo['NOTAS'].apply(lambda x: f"{x:.2f}".replace('.', ',') if isinstance(x, (int, float)) else x)
        df_limpo.to_csv(output, index=False, sep=';', encoding='utf-8', header=False)
        output.seek(0) 

        
        # Botão para baixar o arquivo tratado como .txt
        st.download_button(
            label="⬇ Baixar Notas Tratadas (TXT)",
            data=output,
            file_name=f"{disciplina}_{turma}_{prova}_{etapa}.txt",
            mime="text/plain"
        )