import os 
import streamlit as st
import pandas as pd

# Estilo personalizado para os botões
st.markdown(
    """
    <style>
        /* Estilização dos botões */
        .stButton>button {
            background-color: #5C2D91 !important;  /* Roxo ICEV */
            color: white !important;
            border-radius: 10px;
            padding: 10px 15px;
            font-size: 16px;
            border: none;
            transition: background-color 0.3s ease, transform 0.2s ease;
        }

        /* Efeito ao passar o mouse - mantém a visibilidade */
        .stButton>button:hover {
            background-color: #48207E !important; /* Roxo mais escuro */
            transform: scale(1.05); /* Efeito de leve crescimento */
        }
    </style>
    """,
    unsafe_allow_html=True
)

# Caminho do arquivo onde os dados de alunos são armazenados
ARQUIVO_ALUNOS = "alunos.csv"

# Função para carregar dados de alunos com base no tipo de arquivo
def carregar_dados_alunos():
    if os.path.exists(ARQUIVO_ALUNOS):
        if ARQUIVO_ALUNOS.endswith('.csv'):
            df = pd.read_csv(ARQUIVO_ALUNOS)  # Lê um arquivo CSV
        elif ARQUIVO_ALUNOS.endswith('.xlsx'):
            df = pd.read_excel(ARQUIVO_ALUNOS)  # Lê um arquivo Excel
        elif ARQUIVO_ALUNOS.endswith('.txt'):
            df = pd.read_csv(ARQUIVO_ALUNOS, delimiter='\t')  # Lê um arquivo TXT
        else:
            st.warning("Formato de arquivo não suportado!")
            return pd.DataFrame()
        return df
    else:
        st.warning("Arquivo de dados dos alunos não encontrado!")
        return pd.DataFrame()

# Função para substituir o arquivo de dados dos alunos
def substituir_arquivo_alunos(novo_arquivo):
    file_extension = novo_arquivo.name.split('.')[-1]
    if file_extension == 'csv':
        df_novo = pd.read_csv(novo_arquivo, delimiter= ',')  # Lê o novo arquivo CSV
    elif file_extension == 'xlsx':
        df_novo = pd.read_excel(novo_arquivo)  # Lê o novo arquivo Excel
    elif file_extension == 'txt':
        df_novo = pd.read_csv(novo_arquivo, delimiter='\t')  # Lê o novo arquivo TXT
    else:
        st.warning("Formato de arquivo não suportado!")
        return
    
    if file_extension == 'csv':
        df_novo.to_csv(ARQUIVO_ALUNOS, index=False)  # Salva como CSV
    elif file_extension == 'xlsx':
        df_novo.to_excel(ARQUIVO_ALUNOS, index=False)  # Salva como Excel
    elif file_extension == 'txt':
        df_novo.to_csv(ARQUIVO_ALUNOS, index=False, sep='\t')  # Salva como TXT
    st.success("Dados de alunos substituídos com sucesso!")

# Interface do Streamlit
st.title("📚 Gerenciamento de Dados de Alunos")

# Opção para carregar dados e visualizar
st.subheader("📥 Importar e Substituir Dados de Alunos")
uploaded_file = st.file_uploader("Escolha um arquivo (CSV, Excel ou TXT)", type=["csv", "xlsx", "txt"])

if uploaded_file is not None:
    # Mostrar uma prévia dos dados
    file_extension = uploaded_file.name.split('.')[-1]
    if file_extension == 'csv':
        df_novo = pd.read_csv(uploaded_file, encoding="uft-8")
    elif file_extension == 'xlsx':
        df_novo = pd.read_excel(uploaded_file)
    elif file_extension == 'txt':
        df_novo = pd.read_csv(uploaded_file, delimiter='\t')
    
    st.write("📋 Prévia do arquivo enviado:")
    print(file_extension)
    st.dataframe(df_novo.head())

    # Substituir o arquivo atual com os novos dados
    if st.button("🔄 Substituir Dados"):
        substituir_arquivo_alunos(uploaded_file)

# Exibir os dados atuais de alunos
st.subheader("📊 Dados Atuais dos Alunos")
dados_atual = carregar_dados_alunos()

if not dados_atual.empty:
    st.dataframe(dados_atual)
else:
    st.write("Nenhum dado de aluno disponível.")
