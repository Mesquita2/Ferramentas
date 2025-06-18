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
    
df_alunos = st.session_state["dados"].get("dntoficina")
df_base = df_alunos.copy()
    
    
def carregar_dados(uploaded_file):
    """
    Carrega os dados do arquivo Excel enviado pelo usuário.
    """
    try:
        df = pd.read_excel(uploaded_file, engine='openpyxl')
        return df
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo: {e}")
        return pd.DataFrame()  # Retorna um DataFrame vazio em caso de erro
    
def ajustes_dataframe(df): 
    # Ajusta o DataFrame para garantir que as colunas estejam corretas
    df['Student ID'] = df['Student ID'].astype(str).str.zfill(7)
    df['NOMEALUNO'] = df['Student First Name'].fillna('') + ' ' + df['Student Last Name'].fillna('')
    df['NOMEALUNO'] = df['NOMEALUNO'].str.strip()
    df = df[df['Student ID'] != '0']  
    df = df[df['ALUNO'] != ''] 
    df.rename(columns={'Student ID': 'RA'}, inplace=True)
    return df
    
    
# Interface do Streamlit
st.title("Tratamento de Notas Simulado e REC Simulado")

cursos_disponiveis = sorted(df_base['CURSO'].dropna().unique())

# 1️⃣ Primeiro: Seleção do Curso
curso_selecionado = st.selectbox(
    "Selecione o curso para filtrar as disciplinas:",
    index=None,
    options=cursos_disponiveis
)

if curso_selecionado:
    # 2️⃣ Segundo: Exibir apenas se o Curso já foi selecionado
    turmas_disponiveis = sorted(
        df_base[df_base['CURSO'] == curso_selecionado]['TURMADISC'].dropna().unique()
    )

    turma_selecionada = st.multiselect(
        "Selecione a Turma para filtrar as disciplinas:",
        options=turmas_disponiveis
    )

    if turma_selecionada:
        disciplinas_disponiveis = sorted(
            df_base[
                (df_base['CURSO'] == curso_selecionado) &
                (df_base['TURMADISC'].isin(turma_selecionada))
            ]['DISCIPLINA'].dropna().unique()
        )

        disciplinas_selecionadas = st.multiselect(
            "Selecione as Disciplinas que NÃO são aplicadas no Simulado:",
            options=disciplinas_disponiveis,
            default=[]
        )
        if turma_selecionada:
            uploaded_file = st.file_uploader("Envie o arquivo de notas (Excel)", type=["xlsx"])


        # Carregar e limpar os dados
        if uploaded_file:
            df_original = carregar_dados(uploaded_file)
            st.subheader("Dados Originais")
            st.dataframe(df_original)
            # Funçao ajuste de dataframes
            df_ajustado_zipgrade = ajustes_dataframe(df_original)

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
