import os 
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Alteração de Dados", page_icon="🔄", layout="wide")

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

# Autenticação
users = st.secrets["auth"]

def login():
    st.sidebar.header("Login")
    username = st.sidebar.text_input("Usuário")
    password = st.sidebar.text_input("Senha", type="password")
    
    if username in users and users[username] == password:
        st.session_state["authenticated"] = True
        st.sidebar.success("Login bem-sucedido!")
    else:
        st.sidebar.error("Usuário ou senha incorretos!")

# **🚨 Interrompe tudo caso o usuário não esteja autenticado**
if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    login()
    login_button = st.sidebar.button("Login") 
    st.stop()

# Função para carregar dados de alunos
def carregar_dados_alunos():
    if os.path.exists(ARQUIVO_ALUNOS):
        if ARQUIVO_ALUNOS.endswith('.xlsx'):
            return pd.read_excel(ARQUIVO_ALUNOS)
        else:
            st.warning("Formato de arquivo não suportado!")
    else:
        st.warning("Arquivo de dados dos alunos não encontrado!")
    return pd.DataFrame()

# Função para substituir o arquivo de alunos
def substituir_arquivo_alunos(novo_arquivo):
    file_extension = novo_arquivo.name.split('.')[-1]
    if file_extension == 'xlsx':
        df_novo = pd.read_excel(novo_arquivo)
        df_novo.to_excel(ARQUIVO_ALUNOS, index=False)
        st.success("Dados de alunos substituídos com sucesso!")
    else:
        st.warning("Formato de arquivo não suportado para substituição!")

# Interface após login
st.title("📚 Gerenciamento de Dados de Alunos")

# Opção para carregar e visualizar dados
st.subheader("📥 Importar e Substituir Dados de Alunos")
uploaded_file = st.file_uploader("Escolha um arquivo Excel", type=["xlsx"])

if uploaded_file is not None:
    df_novo = pd.read_excel(uploaded_file)
    
    st.write("📋 Prévia do arquivo enviado:")
    st.write(f"Total de linhas: {len(df_novo)}")
    st.write(f"Colunas: {', '.join(df_novo.columns)}")
    st.dataframe(df_novo.head())

    if st.button("🔄 Substituir Dados"):
        substituir_arquivo_alunos(uploaded_file)

# Exibir dados atuais
st.subheader("📊 Dados Atuais dos Alunos")
dados_atual = carregar_dados_alunos()

dados_atual['RA'] = dados_atual['RA'].apply(lambda x: str(x).zfill(7))


if not dados_atual.empty:
    st.dataframe(dados_atual)
else:
    st.write("Nenhum dado de aluno disponível.")
    
