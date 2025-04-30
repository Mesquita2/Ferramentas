import os 
import streamlit as st
import pandas as pd
from auth import check_authentication, logout

st.set_page_config(page_title="Alteração de Dados", 
                   page_icon="", 
                   layout="wide")


# Verifica se o usuário está autenticado
if not check_authentication():
    st.stop()


# Estilo personalizado para os botões
st.markdown(
    """
    <style>
        .stButton>button {
            background-color: #5C2D91 !important;
            color: white !important;
            border-radius: 10px;
            padding: 10px 15px;
            font-size: 16px;
            border: none;
            transition: background-color 0.3s ease, transform 0.2s ease;
        }
        .stButton>button:hover {
            background-color: #48207E !important;
            transform: scale(1.05);
        }
    </style>
    """,
    unsafe_allow_html=True
)

# Caminho do arquivo onde os dados de alunos são armazenados
ARQUIVO_ALUNOS = "alunos.xlsx"
ARQUIVO_DISCIPLINA = "disciplinas.xlsx"

# Autenticação
users = st.secrets["authentication"]

# Função para carregar dados de alunos
@st.cache_resource
def carregar_dados_alunos(opcao):
    if opcao == 'alunos':
        if os.path.exists(ARQUIVO_ALUNOS):
            if ARQUIVO_ALUNOS.endswith('.xlsx'):
                return pd.read_excel(ARQUIVO_ALUNOS)
            else:
                st.warning("Formato de arquivo não suportado!")
        else:
            st.warning("Arquivo de dados dos alunos não encontrado!")
    elif opcao == 'disciplina':
        if os.path.exists(ARQUIVO_DISCIPLINA):
            if ARQUIVO_DISCIPLINA.endswith('.xlsx'):
                return pd.read_excel(ARQUIVO_DISCIPLINA)
            else:
                st.warning('Formato de arquivo não suportado!')
        else:
            st.warning("Arquivo de dados das disciplinas não encontrado!")    
    return pd.DataFrame()

# Função para substituir o arquivo de alunos
def substituir_arquivo_alunos(novo_arquivo, opcao):
    if opcao == 'alunos':
        file_extension = novo_arquivo.name.split('.')[-1]
        if file_extension == 'xlsx':
            df_novo = pd.read_excel(novo_arquivo)
            df_novo.rename(columns={'NOMEDISCIPLINA': 'DISCIPLINA',
                                'NOMECURSO': 'CURSO',
                                'NOMEALUNO': 'ALUNO'}, inplace=True)
            df_novo = df_novo[df_novo['NOMESTATUS'] != 'Cancelamento']
            df_novo.to_excel(ARQUIVO_ALUNOS, index=False)
            df_novo['RA'] = df_novo['RA'].apply(lambda x: str(x).zfill(7))
            st.success("Dados de alunos substituídos com sucesso!")
        else:
            st.warning("Formato de arquivo não suportado para substituição!")
    elif opcao == 'disciplinas':
        file_extension = novo_arquivo.name.split('.')[-1]
        if file_extension == 'xlsx':
            df_novo = pd.read_excel(novo_arquivo)
            df_novo.to_excel(ARQUIVO_DISCIPLINA, index=False)
            st.success("Dados de alunos substituídos com sucesso!")
            
def dash(df):
    if not df:
        st.write("Data frame Vazio")
        return pd.DataFrame() 
    if not os.path.exists(df):
        st.write(f"Erro: Arquivo '{df}' não encontrado.")
        return pd.DataFrame()  
    return pd.read_excel(df) 


# Interface após login
st.title("Gerenciamento de Dados de Alunos")

st.subheader("Qual opção deseja fazer o updownload ?")
ARQUIVO = st.selectbox("Selecione uma opção", ['alunos' , 'disciplinas'])

# Opção para carregar e visualizar dados
st.subheader("Importar e Substituir Dados de Alunos")
uploaded_file = st.file_uploader("Escolha um arquivo Excel", type=["xlsx"])
#
if uploaded_file is not None:
    df_novo = pd.read_excel(uploaded_file)
    
    st.write("Prévia do arquivo enviado:")
    st.write(f"Total de linhas: {len(df_novo)}")
    st.write(f"Colunas: {', '.join(df_novo.columns)}")
    st.dataframe(df_novo.head())

    if st.button(":: Substituir Dados"):
        substituir_arquivo_alunos(uploaded_file, ARQUIVO)

# Exibir dados atuais
st.subheader("Dados Atuais dos Alunos")
if not ARQUIVO_ALUNOS:
    st.write("Data Frame Vazio")
elif not os.path.exists(ARQUIVO_ALUNOS):  
    st.write(f" O arquivo '{ARQUIVO_ALUNOS}' não existe. Verifique o caminho ou envie o arquivo.")
else:
    dados_atual = dash(ARQUIVO_ALUNOS)
    if not dados_atual.empty:
        dados_atual['RA'] = dados_atual['RA'].apply(lambda x: str(x).zfill(7))
        st.dataframe(dados_atual[['CODTURMA','CURSO','ALUNO', 'RA']])

st.subheader("Dados Disciplinas")
if not ARQUIVO_DISCIPLINA:
    st.write("Data frame Vazio")
elif not os.path.exists(ARQUIVO_DISCIPLINA):  
    st.write(f"O arquivo '{ARQUIVO_DISCIPLINA}' não existe. Verifique o caminho ou envie o arquivo. ")
else:
    dados_disciplina = dash(ARQUIVO_DISCIPLINA)
    if not dados_disciplina.empty:  # Verifica se o DataFrame não está vazio
        st.dataframe(dados_disciplina[['CODTURMA','NOME','IDMOODLE']]) # teste 

