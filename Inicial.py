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
ARQUIVO_ALUNOS = "alunos.xlsx"  # Alterado para um arquivo Excel

# Função para carregar dados de alunos com base no tipo de arquivo
def carregar_dados_alunos():
    if os.path.exists(ARQUIVO_ALUNOS):
        if ARQUIVO_ALUNOS.endswith('.xlsx'):
            df = pd.read_excel(ARQUIVO_ALUNOS)  # Lê um arquivo Excel
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
    if file_extension == 'xlsx':
        df_novo = pd.read_excel(novo_arquivo)  # Lê o novo arquivo Excel
        df_novo.to_excel(ARQUIVO_ALUNOS, index=False)  # Salva como Excel
        st.success("Dados de alunos substituídos com sucesso!")
    else:
        st.warning("Formato de arquivo não suportado para substituição!")

# Interface do Streamlit
st.title("📚 Gerenciamento de Dados de Alunos")

# Opção para carregar dados e visualizar
st.subheader("📥 Importar e Substituir Dados de Alunos")
uploaded_file = st.file_uploader("Escolha um arquivo Excel", type=["xlsx"])

if uploaded_file is not None:
    df_novo = pd.read_excel(uploaded_file)
    
    st.write("📋 Prévia do arquivo enviado:")
    st.write(f"Total de linhas: {len(df_novo)}")
    st.write(f"Colunas: {', '.join(df_novo.columns)}")
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
