
import streamlit as st
import pandas as pd
import io
from auth import check_authentication

# Configuração da página
st.set_page_config(page_title="Limpeza de Notas",
                   page_icon="", # Criar icon Icev 
                   layout="wide")

if not check_authentication():
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
    elif prova == "Recuperação":
        df_teste = df_teste.dropna(subset=['NOTAS'])
        df_teste = df_teste[df_teste['NOTAS'] != 0]
    elif prova == "Quizz":
        df_teste = df_teste.dropna(subset=['NOTAS'])


    return df_teste

# Interface do Streamlit
st.title("Limpeza e Tratamento de Notas")

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

# Carregar e limpar os dados
if uploaded_file:
    df_original = carregar_dados(uploaded_file)
    st.subheader("Dados Originais")
    st.dataframe(df_original)
    
    disciplina = df_original['DISCIPLINA'].iloc[0]
    turma = df_original['TURMADISC'].iloc[0]
    
    # Limpar dados
    df_limpo = limpar_dados(df_original, prova, etapa, codetapa, codprova, tipoetapa)
    st.subheader("Dados Após Limpeza")    
    st.dataframe(df_limpo)
    
    
    df_limpo['RA'] = df_limpo['RA'].astype(str)
    df_limpo['RA'] = df_limpo['RA'].apply(lambda x: str(x).zfill(7))# Remove espaços e substitui vírgula por ponto
    df_limpo['NOTAS'] = pd.to_numeric(df_limpo['NOTAS'], errors='coerce') # Converte para float (NaN se não conseguir)

    if (df_limpo['NOTAS'] > 8).any():
        st.info("Existem alunos com nota maior que 8.")

    
    # Criar o arquivo .txt com separador ';'
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
