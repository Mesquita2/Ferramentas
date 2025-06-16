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

df_alunos = st.session_state["dados"].get("alunosxdisciplinas")
df_base = df_alunos.copy()

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
    
import pandas as pd

def calcula_qtd_questoes(df):
    
    df['Questoes'] = 0

    
    credito_to_questoes = {4: 16, 2: 8}
    
    credito_to_questoes_dir = {4: 12, 2: 6}
    
    df.loc[df['CURSO'] == 'Bacharelado em Direito', 'Questoes'] = \
        df['NUMCREDITOSCOB'].map(credito_to_questoes_dir).fillna(0).astype(int)

    df.loc[df['CURSO'] != 'Bacharelado em Direito', 'Questoes'] = \
        df['NUMCREDITOSCOB'].map(credito_to_questoes).fillna(0).astype(int)


    resultado = df.groupby(['ALUNO', 'RA'])['Questoes'].sum().reset_index()
    resultado = resultado.drop_duplicates(subset=['ALUNO', 'RA'])

    #O retorno é os alunos e a quantidade de questoes que devem ter no simulado. 
    #Lembrar que exite regras e apenas chamar apos retirar as disciplinas que nao vao ser ultilizadas. 
    return resultado


# Função para limpar os dados
@st.cache_data
def limpar_dados(df, prova, etapa, codetapa, codprova, tipoetapa, questoes_anuladas, disciplinas_excluidas):
    
    df_alunos = st.session_state["dados"].get("alunosxdisciplinas")
    df_base = df_alunos.copy()
    
    df_base = df_alunos.copy()
    df_base = df_base[~df_base['DISCIPLINA'].isin(disciplinas_excluidas)]
    
    #Funcao para saber quantidades de possiveis pontos que se baseam em carga horaria
    # ENG ou DIR ou ADM
    
    # Comparar df_base com o df que vou mandar para calcula_qtd_questoes.
    # Comparar o df_base['Points Earned'] como o df['Questoes'].
    # O df deve conter o calculo baseado nas disciplinas que estao matriculados entao veremos se bate com o que ta no simulado.
    # Fazer todos que estao diferentes ira para um df diferente que sera revisado antes de colocar a nota.
    df_questoes = calcula_qtd_questoes(df_base)
    df.rename(columns={'Student ID': 'RA',}, inplace=True)
    # Ajuste para merge, garantindo que o RA do DF original esteja no formato certo
    df['RA'] = df['RA'].astype(str).str.zfill(7)

    # Agrupar df_original para obter os Possible Points totais por aluno
    df_simulado_pontos_possiveis = df.groupby('RA')['Possible Points'].sum().reset_index()
    df_simulado_pontos_possiveis.rename(columns={'Possible Points': 'PontosSimulado'}, inplace=True)

    # Realiza o merge entre as questões esperadas e os pontos possíveis do simulado
    df_validacao = pd.merge(df_questoes, df_simulado_pontos_possiveis, on='RA', how='left')

    # Calcula a diferença entre as questões esperadas e as que o aluno fez no simulado
    df_validacao['DiferencaQuestoes'] = df_validacao['Questoes'] - df_validacao['PontosSimulado'].fillna(0)

    # Filtra alunos com discrepâncias
    df_discrepancias = df_validacao[df_validacao['DiferencaQuestoes'] != 0]

    # Exibe o DataFrame de discrepâncias para revisão, se houver
    if not df_discrepancias.empty:
        st.subheader(" Alunos com Discrepâncias entre Questões Esperadas e Pontos do Simulado ")
        st.write("Atenção: A quantidade de questões esperadas para estes alunos difere dos 'Possible Points' no arquivo do simulado. Isso pode indicar que disciplinas não consideradas ou pontos extras/faltantes no simulado precisam ser revisados manualmente.")
        # Exibe apenas as colunas relevantes para a revisão
        st.dataframe(df_discrepancias[['ALUNO', 'RA', 'Questoes', 'PontosSimulado', 'DiferencaQuestoes']])
        st.warning("Recomenda-se uma verificação manual para estes casos antes de finalizar as notas.")
    
        
    # Ajuste para merge
    df_base['RA'] = df_base['RA'].apply(lambda x: str(x).zfill(7))
    df['RA'] = df['RA'].fillna(0)
    df['RA'] = df['RA'].astype(int).astype(str).str.zfill(7)
    
    df_base.rename(columns={'NOMEDISCIPLINA': 'DISCIPLINA',
                            'NOMECURSO': 'CURSO',
                            'NOMEALUNO': 'ALUNO'}, inplace=True)
    
    df['ALUNO'] = df['Student First Name'].fillna('') + ' ' + df['Student Last Name'].fillna('')
    df['ALUNO'] = df['ALUNO'].str.strip()
    
    # Calcular pontuação extra por anulação de questões
    anuladas_total = pd.Series(0, index=df['RA'].astype(str).str.zfill(7).unique())

    for q in questoes_anuladas:
        col_nome = f"#{q} Points Earned"
        if col_nome in df.columns:
            questao = df[col_nome].fillna(0)
            ganho_extra = (questao == 0).astype(int)
            ids = df['RA'].astype(str).str.zfill(7)
            bonus = pd.Series(ganho_extra.values, index=ids)
            bonus = bonus.groupby(bonus.index).sum() 
            anuladas_total = anuladas_total.add(bonus, fill_value=0)

    # Calculo da nota do simulado
    df['Earned Points Original'] = df['Earned Points'].fillna(0)
    df['Bonus Anuladas'] = df['RA'].astype(str).str.zfill(7).map(anuladas_total).fillna(0)
    df['Earned Points Final'] = df['Earned Points Original'] + df['Bonus Anuladas']

    possible_points = df['Possible Points'].replace(0, np.nan)
    proporcao = (df['Earned Points Final'] * 1.25) / possible_points
    df['NOTAS'] = np.minimum(proporcao, 1.0).fillna(0) * 10
    
    st.subheader("Dados Originais")
    st.dataframe(df)

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

#Limpeza Disciplinas que nao fazem parte
cursos_disponiveis = sorted(df_base['CURSO'].dropna().unique())
curso_selecionado = st.selectbox(
    "Selecione o curso para filtrar as disciplinas:",
    options=cursos_disponiveis
)
disciplinas_disponiveis = sorted(
    df_base[df_base['CURSO'] == curso_selecionado]['DISCIPLINA'].dropna().unique()
)
disciplinas_selecionadas = st.multiselect(
    "Selecione as Disciplinas que nao sao aplicadas no Simulado : ",
    options= disciplinas_disponiveis,
    default=[]
)

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
    
    # Definir as variáveis de configuração para o filtro
    etapa = "P3"
    prova = st.selectbox('Selecione o tipo de prova', ['Prova', 'Recuperação'])
    tipoetapa = 'N'  # Tipo de etapa
    codetapa = 3  # Código da etapa
    codprova = 1  # Código da prova


    questoes_anuladas_input = st.text_input("Informe os números das questões anuladas (separados por vírgula):", value="")
    questoes_anuladas = [int(q.strip()) for q in questoes_anuladas_input.split(",") if q.strip().isdigit()]

    # Limitar as opções de Etapa com base na escolha da Prova
    if prova == "Prova":
        codprova = 1  # Prova = 1
    elif prova == "Recuperação":
        codprova = 2  # Recuperação = 2
        
    if st.button("Calcular Notas com Anulações"):
        df_limpo = limpar_dados(df_original, prova, etapa, codetapa, codprova, tipoetapa, questoes_anuladas, disciplinas_selecionadas)

        st.subheader("Dados Após Limpeza")
        st.dataframe(df_limpo)

        df_limpo['RA'] = df_limpo['RA'].astype(str)
        df_limpo['RA'] = df_limpo['RA'].apply(lambda x: str(x).zfill(7))
        df_limpo['NOTAS'] = df_limpo['NOTAS'].apply(lambda x: f"{x:.2f}".replace('.', ',') if isinstance(x, (int, float)) else x)

        # Criar o arquivo .txt com separador ';'
        output = io.BytesIO()
        df_limpo.to_csv(output, index=False, sep=';', encoding='utf-8', header=False)
        output.seek(0)

        classe = df_limpo['TURMADISC'].iloc[0] if not df_limpo.empty else "sem_classe"

        # Botão para baixar o arquivo tratado como .txt
        st.download_button(
            label="⬇ Baixar Notas Tratadas (TXT)",
            data=output,
            file_name=f"{classe}_{prova}.txt",
            mime="text/plain"
        )
