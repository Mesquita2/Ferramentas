import io
import streamlit as st
from auth import check_authentication
import pandas as pd
import numpy as np

# Configuração da página
st.set_page_config(page_title="Limpeza Simulado e REC Simulado",
                   page_icon="", # Criar icon Icev 
                   layout="wide")

if not check_authentication():
    st.stop()

# Recebe dados do Zip
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
def limpar_dados(df, prova, etapa, codetapa, codprova, tipoetapa, anuladas, df_editado):
    df_alunos = st.session_state["dados"].get("alunosxdisciplinas")
    df_base = df_alunos.copy()
    
    # Ajuste para merge
    df_base['RA'] = df_base['RA'].apply(lambda x: str(x).zfill(7))
    df['Student ID'] = df['Student ID'].fillna(0)
    df['Student ID'] = df['Student ID'].astype(int).astype(str).str.zfill(7)
    df_base.rename(columns={'NOMEDISCIPLINA': 'DISCIPLINA',
                            'NOMECURSO': 'CURSO',
                            'NOMEALUNO': 'ALUNO'}, inplace=True)
    
    df['ALUNO'] = df['Student First Name'].fillna('') + ' ' + df['Student Last Name'].fillna('')
    df['ALUNO'] = df['ALUNO'].str.strip()

    # Recuperar anuladas individuais do df_editado e somar com global
    anuladas_individual = df_editado.groupby('Student ID')['Anuladas_Individuais'].sum().fillna(0)
    anuladas_individual.index = anuladas_individual.index.map(lambda x: str(x).zfill(7))
    anuladas_total = anuladas_individual.add(anuladas, fill_value=anuladas)


    # Calculo da nota do simulado
    earned_points = df['Earned Points'].fillna(0)
    possible_points = df['Possible Points'].replace(0, np.nan)
    pontos_com_anuladas = earned_points + df['Student ID'].map(anuladas_total)
    proporcao = (pontos_com_anuladas * 1.25) / possible_points
    df['NOTAS'] = np.minimum(proporcao, 1.0).fillna(0) * 10

    # Configurando e ajustando dataframe 
    df.rename(columns={'Student ID': 'RA',
                       'NOMEALUNO': 'ALUNO'}, inplace=True)
    df = pd.merge(df_base, df[['RA',  'NOTAS']],
                  on=['RA'],
                  how='left') 
    df = df.copy()
    
    # Adicionar as novas colunas
    df['CODETAPA'] = codetapa
    df['CODPROVA'] = codprova
    df['TIPOETAPA'] = tipoetapa
    df['PROVA'] = prova
    df['ETAPA'] = etapa

    # Nova ordem das colunas
    colunas = ['CODCOLIGADA', 'CURSO', 'TURMADISC', 'IDTURMADISC', 'DISCIPLINA', 'RA', 'ALUNO', 'ETAPA', 'PROVA', 'TIPOETAPA', 'CODETAPA', 'CODPROVA', 'NOTAS']
    df = df[colunas]

    # Condicional para a limpeza das notas
    df_final = df.copy()
    if prova == "Prova":
        df_final = df_final.dropna(subset=['NOTAS']) 
    elif prova == "Recuperação":
        df_final = df_final[(df_final['NOTAS'] != 0) & (df_final['NOTAS'].notna())]

    return df_final

# Interface do Streamlit
st.title("Tratamento de Notas Simulado e REC Simulado")

# Upload do arquivo Excel
uploaded_file = st.file_uploader("Envie o arquivo de notas (Excel)", type=["xlsx"])

# Carregar e limpar os dados
if uploaded_file:
    df_original = carregar_dados(uploaded_file)
    st.subheader("Dados Originais")
    st.dataframe(df_original)
    df_original['Anuladas_Individuais'] = 0
    df_original['ALUNO'] = df_original['Student First Name'].fillna('') + ' ' + df_original['Student Last Name'].fillna('')
    df_original['ALUNO'] = df_original['ALUNO'].str.strip()
    df_original['Student ID'] = df_original['Student ID'].fillna(0)
    df_original = df_original[df_original['Student ID'] != 0]

    # Editor para inserir anuladas por aluno
    df_editado = st.data_editor(
        df_original[['Student ID', 'ALUNO', 'Anuladas_Individuais']],
        num_rows="dynamic",
        use_container_width=True
    )
    
    # Definir as variáveis de configuração para o filtro
    etapa = "P3"
    prova = st.selectbox('Selecione o tipo de prova', ['Prova', 'Recuperação'])
    tipoetapa = 'N'  # Tipo de etapa
    codetapa = 3  # Código da etapa
    codprova = 1  # Código da prova

    anuladas = st.number_input("Indique o número de questões anuladas:", min_value=0, max_value=50, step=1)
    anuladas = int(anuladas)

    # Limitar as opções de Etapa com base na escolha da Prova
    if prova == "Prova":
        codprova = 1  # Prova = 1
    elif prova == "Recuperação":
        codprova = 2  # Recuperação = 2
        
    # Limpar dados
    df_limpo = limpar_dados(df_original, prova, etapa, codetapa, codprova, tipoetapa, anuladas, df_editado)
    st.subheader("Dados Após Limpeza")
    st.dataframe(df_limpo)
    df_limpo['RA'] = df_limpo['RA'].astype(str)
    df_limpo['RA'] = df_limpo['RA'].apply(lambda x: str(x).zfill(7))
    df_limpo['NOTAS'] = df_limpo['NOTAS'].apply(lambda x: f"{x:.2f}".replace('.', ',') if isinstance(x, (int, float)) else x)

    # Criar o arquivo .txt com separador ';'
    output = io.BytesIO()  
    df_limpo.to_csv(output, index=False, sep=';', encoding='utf-8', header=False)
    output.seek(0) 

    classe = df_limpo['TURMADISC'].iloc() if not df_limpo.empty else "sem_classe"
    
    
    # Botão para baixar o arquivo tratado como .txt
    st.download_button(
        label="⬇ Baixar Notas Tratadas (TXT)",
        data=output,
        file_name=f"{classe}_{prova}.txt",
        mime="text/plain"
    )