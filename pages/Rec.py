from datetime import date
import os
from docx import Document
from docx.shared import Pt, RGBColor
from docx.shared import Inches
import streamlit as st
import pandas as pd
import io
from auth import check_authentication

imagem_rodape = "Endereço.jpeg"
imagem_cabecalho = 'Logo.jpg'
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
        df_base = pd.read_excel('alunos.xlsx')
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
        
        
        df = df.drop_duplicates(subset=['ALUNO', 'DISCIPLINA', 'TURMADISC', 'RA'])
        df.to_excel(ARQUIVOREC, index=False)
        df['RA'] = df['RA'].apply(lambda x: str(x).zfill(7))
        st.success("Dados de alunos substituídos com sucesso!")
    else:
        st.warning("Formato de arquivo não suportado para substituição!")
        
def adicionar_imagem_no_cabecalho(doc, imagem_cabecalho):
    # Acessando o cabeçalho da primeira seção do documento
    section = doc.sections[0]
    header = section.header

    # Criando um parágrafo no cabeçalho e adicionando uma imagem
    paragraph = header.paragraphs[0]  # Usando o primeiro parágrafo do cabeçalho
    section.header_distance = Inches(0.2)   
    run = paragraph.add_run()

    # Adicionando a imagem ao cabeçalho
    run.add_picture(imagem_cabecalho, width=Inches(7.5), height=Inches(1))  # Ajuste o tamanho conforme necessário

def adicionar_imagem_no_rodape(doc, imagem_rodape):
    # Acessando o rodapé da primeira seção do documento
    section = doc.sections[0]
    footer = section.footer
    

    # Criando um parágrafo no rodapé e adicionando uma imagem
    paragraph = footer.paragraphs[0]  # Usando o primeiro parágrafo do rodapé
    section.footer_distance = Inches(0.2)
    run = paragraph.add_run()

    # Adicionando a imagem ao rodapé
    run.add_picture(imagem_rodape, width=Inches(7.5), height=Inches(1))  # Ajuste o tamanho conforme necessário


def gerar_relatorio(df, disciplina, turma):
      
    dataatual = date.today().strftime('%d/%m/%Y')
    
    df = df_rec[(df_rec["DISCIPLINA"] == disciplina) & (df_rec["TURMADISC"] == turma)]
    df = df.sort_values(by="ALUNO", ascending = True)
    doc = Document()
    
    adicionar_imagem_no_cabecalho(doc, imagem_cabecalho)
    adicionar_imagem_no_rodape(doc, imagem_rodape)
    
    #Ajustar margens da página para estreitas
    section = doc.sections[0]
    section.left_margin = Inches(0.5) 
    section.right_margin = Inches(0.5)
    section.top_margin = Inches(0.5)  
    section.bottom_margin = Inches(0.5) 
    
    
    # Adicionando título "Disciplina" com personalização
    p = doc.add_paragraph()
    run = p.add_run("\n\n")
    run = p.add_run(f"Disciplina: {disciplina}")
    run.font.name = 'Arial'           # Definindo a fonte para Arial
    run.font.size = Pt(14)            # Tamanho da fonte para 14 pt
    run.font.color.rgb = RGBColor(0, 0, 0)  # Cor preta (RGB: 0,0,0)
    
    # Adicionando título "Turma" com personalização
    p = doc.add_paragraph()
    run = p.add_run(f"Turma: {turma}")
    run.font.name = 'Arial'
    run.font.size = Pt(12)            
    run.font.color.rgb = RGBColor(0, 0, 0)
    
    p = doc.add_paragraph()
    run = p.add_run(f"Data: {dataatual}")
    run.font.name = 'Arial'
    run.font.size = Pt(12)            
    run.font.color.rgb = RGBColor(0, 0, 0)
    
    
    
    colunas = ['ALUNO']
    df = df[colunas]
    df['ASSINATURA'] = '  '
    # Adiciona a tabela
    table = doc.add_table(rows=1, cols=len(df.columns))
    table.style = 'Table Grid'


    # Cabeçalho da tabela
    hdr_cells = table.rows[0].cells
    for i, col_name in enumerate(df.columns):
        hdr_cells[i].text = col_name

    # Dados
    for _, row in df.iterrows():
        row_cells = table.add_row().cells
        for i, item in enumerate(row):
            row_cells[i].text = str(item)


    # Salva em memória
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

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

    if st.button(":: Substituir Dados"):
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
    df_filtrado['NOTAS'] = 0 
    colunas = ['TURMADISC', 'DISCIPLINA', 'RA', 'ALUNO', 'NOTAS']
    df_filtrado = df_filtrado[colunas]
    
    df_filtrado = df_filtrado.sort_values(by ="ALUNO", ascending= True)
    
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
disciplina = st.selectbox("Escolha a disciplina", disciplinas)

turmas_filtradas = df_rec[df_rec["DISCIPLINA"] == disciplina]["TURMADISC"].unique().tolist()
turma = st.selectbox("🏫 Escolha a turma", turmas_filtradas)

prova = st.selectbox("Escolha se é REC_P1 ou REC_P2", ["REC_P1", "REC_P2"])

df_filtrado = df_rec[(df_rec["DISCIPLINA"] == disciplina) & (df_rec["TURMADISC"] == turma)]
st.write(f"**Alunos da Disciplina: {disciplina} | Turma: {turma}**")
total = df_filtrado['ALUNO'].count()
st.write(f"**Quatidade de REC solicitadas: {total}**")
df_filtrado = df_filtrado.sort_values(by ="ALUNO", ascending= True)
st.dataframe(df_filtrado[["ALUNO", "DISCIPLINA", "TURMADISC"]])


if disciplina and turma:
    excel_file = gerar_excel(df_rec, disciplina, turma)
    st.download_button(
        label="⬇ Gerar e Baixar Planilha Excel",
        data=excel_file,
        file_name=f"{disciplina}_{turma}_{prova}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
        
st.title("Criar Relatorio de Assinatura")
if disciplina and turma:
    relatorio = gerar_relatorio(df_rec, disciplina, turma)
    st.download_button(
        label="Gerar e Baixar Relatorio de Assinaturas",
        data= relatorio,
        file_name=f"{disciplina}_{turma}_{prova}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )    
    
