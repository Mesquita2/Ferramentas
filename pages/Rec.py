import streamlit as st
import pandas as pd
import io


# Configuração da página
st.set_page_config(page_title="Limpeza Dados REC", page_icon=" ", layout="wide")

st.warning("Estamos em obra !!")
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
    df_base = pd.read_excel("alunos.xlsx")

    df_base['RA'] = df_base['RA'].apply(lambda x: str(x).zfill(7))
    df['RA'] = df['RA'].apply(lambda x: str(x).zfill(7))
    # Renomear colunas
    df_base.rename(columns={'NOMEDISCIPLINA': 'DISCIPLINA',
                            'NOMECURSO': 'CURSO',
                            'NOMEALUNO': 'ALUNO'}, inplace=True)
    
    df.rename(columns={'NOMEDISCIPLINA': 'DISCIPLINA',
                       'NOMECURSO': 'CURSO',
                       'NOMEALUNO': 'ALUNO'}, inplace=True)
    
    df = pd.merge(df_base, df[['DISCIPLINA', 'ALUNO', 'RA',  'NOTAS']],
                  on=['DISCIPLINA', 'ALUNO', 'RA'],
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
    df_teste = df[colunas]

    return df_teste

# Interface do Streamlit
st.title("Limpeza e tratamento de notas de REC")

# Upload do arquivo Excel
uploaded_file = st.file_uploader("📤 Envie o arquivo de notas (Excel)", type=["xlsx"])

# Definir as variáveis de configuração para o filtro
etapa = st.selectbox('Selecione a etapa', ['REC_P1', 'REC_P2'])
tipoetapa = 'N'  # Tipo de etapa
codetapa = 2  # Código da etapa
codprova = 1  # Código da prova
prova = 'Recuperação'

if etapa == 'REC_P1' :
    codetapa = 1  # P1 = 1
    codprova = 2  # Recuperação = 2
elif etapa == 'REC_P2':
    codetapa = 2  # P2 = 2
    codprova = 2  # Recuperação = 2

# Carregar e limpar os dados
if uploaded_file:
    df_original = carregar_dados(uploaded_file)
    st.subheader("📋 Dados Originais")
    st.dataframe(df_original)
    
    disciplina = df_original['DISCIPLINA'].iloc[0]
    turma = df_original['TURMADISC'].iloc[0]
    
    # Limpar dados
    df_limpo = limpar_dados(df_original, prova, etapa, codetapa, codprova, tipoetapa)
    st.subheader("✅ Dados Após Limpeza")
    st.dataframe(df_limpo)
    
    
    df_limpo['RA'] = df_limpo['RA'].astype(str)
    df_limpo['RA'] = df_limpo['RA'].apply(lambda x: str(x).zfill(7))
    df_limpo['NOTAS'] = df_limpo['NOTAS'].apply(lambda x: f"{x:.2f}".replace('.', ','))
    
    # Criar o arquivo .txt com separador ';'
    output = io.BytesIO()  
    df_limpo.to_csv(output, index=False, sep=';', encoding='utf-8', header=False)
    output.seek(0) 

    
    # Botão para baixar o arquivo tratado como .txt
    st.download_button(
        label="⬇ Baixar Notas Tratadas (TXT)",
        data=output,
        file_name=f"{disciplina}_{turma}_{prova}.txt",
        mime="text/plain"
    )

    
