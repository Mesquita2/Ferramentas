import os
import streamlit as st
import pandas as pd
import io
from auth import check_authentication

ARQUIVOREC = 'arquivorec.xlsx'


# Configuração da página
st.set_page_config(page_title="Limpeza Dados da REC", 
                   page_icon=" ", 
                   layout="wide")

if not check_authentication():
    st.stop()
    

    
# Função para carregar o arquivo
@st.cache_resource
def carregar_dados_REC(opcao):
    if os.path.exists(ARQUIVOREC):
        if ARQUIVOREC.endswith('.xlsx'):
            return pd.read_excel(ARQUIVOREC)
        else:
            st.warning("Formato de arquivo não suportado!")
    else:
            st.warning("Arquivo de dados dos alunos não encontrado!")
    return pd.DataFrame()

# Função para substituir o arquivo de alunos
def substituir_arquivo_alunos(novo_arquivo, opcao):
    file_extension = novo_arquivo.name.split('.')[-1].lower()
    if file_extension == 'xlsx':
        df = pd.read_excel(novo_arquivo)
            
        df['VALOR'] = (
            df['VALOR']
             #retirar o codigo em () do nome da disciplina
            .str.replace(r'\s*\(.*?\)', '', regex=True) 
            .str.replace(r'[\u200b\u200e\u202c\u00a0]', '', regex=True) 
            .str.strip()
        )
            
        df.rename(columns={'VALOR': 'DISCIPLINA',
                            'NOME': 'ALUNO',
                            'CODTURMA' : 'TURMADISC',
                            'RA': 'RA'}, inplace=True)
        df.to_excel(ARQUIVOREC, index=False)
        df['RA'] = df['RA'].apply(lambda x: str(x).zfill(7))
        st.success("Dados de alunos substituídos com sucesso!")
    else:
        st.warning("Formato de arquivo não suportado para substituição!")


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
    
    df['nomelimpo'] = df['VALOR'].str.lower().str.strip()
    df.rename(columns={'nomelimpo': 'DISCIPLINA',
                       'CODTURMA': 'TURMADISC',
                       'NOME': 'ALUNO',
                       'RA': 'RA'}, inplace=True)
    
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

def dash(df):
    if not df:
        st.write("Data frame Vazio")
        return pd.DataFrame() 
    if not os.path.exists(df):
        st.write(f"Erro: Arquivo '{df}' não encontrado.")
        return pd.DataFrame()  
    return pd.read_excel(df) 

# Interface do Streamlit
st.title("Limpeza e tratamento de notas de REC")

# Upload do arquivo Excel
uploaded_file = st.file_uploader("Escolha um arquivo Excel da Rec para analise", type=["xlsx"])

if uploaded_file is not None:
    df_novo = pd.read_excel(uploaded_file)
    
    st.write("**Prévia do arquivo enviado:**")
    st.write(f"Total de linhas: {len(df_novo)}")
    st.write(f"Colunas: {', '.join(df_novo.columns)}")
    st.dataframe(df_novo.head())

    if st.button("🔄 Substituir Dados"):
        substituir_arquivo_alunos(uploaded_file, ARQUIVOREC)

        
st.subheader("Dados dos Cadastrados na REC")
if not ARQUIVOREC:
    st.write("Data frame Vazio")
elif not os.path.exists(ARQUIVOREC):  
    st.write(f"**O arquivo '{ARQUIVOREC}' não existe. Verifique o caminho ou envie o arquivo. **")
else:
    dados_disciplina = dash(ARQUIVOREC)
    if not dados_disciplina.empty:  # Verifica se o DataFrame não está vazio
        st.dataframe(dados_disciplina[['DISCIPLINA','ALUNO']]) # teste 


def gerar_excel(df_rec, disciplina, turma):
    df_filtrado = df_rec[(df_rec["DISCIPLINA"] == disciplina) & (df_rec["TURMADISC"] == turma)]
    df_filtrado['RA'] = df_filtrado['RA'].astype(str)
    df_filtrado["NOTAS"] = 0
    colunas = ['TURMADISC', 'DISCIPLINA', 'RA', 'ALUNO', 'NOTAS']
    df_filtrado = df_filtrado[colunas]
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_filtrado.to_excel(writer, index=False, sheet_name="Notas")
    output.seek(0)
    return output

st.title("Gerador de Planilha de Notas para REC")

df_rec = dash(ARQUIVOREC)
if df_rec.empty:
    st.stop()
    
disciplinas = df_rec["DISCIPLINA"].unique().tolist()
disciplina = st.selectbox("📖 Escolha a disciplina", disciplinas)

turmas_filtradas = df_rec[df_rec["DISCIPLINA"] == disciplina]["TURMADISC"].unique().tolist()
turma = st.selectbox("🏫 Escolha a turma", turmas_filtradas)

prova = st.selectbox("Escolha se é REC_P1 ou REC_P2", ["REC_P1", "REC_P2"])

df_filtrado = df_rec[(df_rec["DISCIPLINA"] == disciplina) & (df_rec["TURMADISC"] == turma)]
st.write(f"📝 **Alunos da Disciplina: {disciplina} | Turma: {turma}**")
total = df_filtrado['ALUNO'].count()
st.write(f"📝 **Quatidade de REC solicitadas: {total}**")
st.dataframe(df_filtrado[["ALUNO", "DISCIPLINA", "TURMADISC"]])


if disciplina and turma:
    excel_file = gerar_excel(df_rec, disciplina, turma)
    st.download_button(
        label="Gerar e Baixar Planilha Excel",
        data=excel_file,
        file_name=f"{disciplina}_{turma}_{prova}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
        
    
