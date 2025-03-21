import streamlit as st
import pandas as pd
import io

# Função para carregar os alunos do CSV
def carregar_alunos():
    try:
        df = pd.read_csv("alunos.csv")  # Agora lê do CSV
        return df
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo alunos.csv: {e}")
        return pd.DataFrame()

# Função para gerar a planilha de notas em CSV
def gerar_csv(df_alunos, disciplina, turma):
    df_filtrado = df_alunos[(df_alunos["Disciplina"] == disciplina) & (df_alunos["Turma"] == turma)]
    df_filtrado = df_filtrado[["Nome"]]
    df_filtrado["Nota"] = ""  # Coluna vazia para o professor preencher

    output = io.StringIO()  # Usamos StringIO para manipular texto em memória
    df_filtrado.to_csv(output, index=False)
    output.seek(0)
    return output

# Interface do Streamlit
st.title("📚 Gerador de Planilha de Notas")

df_alunos = carregar_alunos()
if df_alunos.empty:
    st.stop()

# Seleção de disciplina e turma
disciplinas = df_alunos["Disciplina"].unique().tolist()
turmas = df_alunos["Turma"].unique().tolist()

disciplina = st.selectbox("📖 Escolha a disciplina", disciplinas)
turma = st.selectbox("🏫 Escolha a turma", turmas)

# Botão para gerar e baixar a planilha
if st.button("📥 Gerar Planilha CSV"):
    csv_file = gerar_csv(df_alunos, disciplina, turma)
    st.download_button(
        label="⬇ Baixar Planilha",
        data=csv_file,
        file_name=f"{disciplina}_{turma}_notas.csv",
        mime="text/csv"
    )

# Upload de planilha preenchida
uploaded_file = st.file_uploader("📤 Envie o arquivo CSV preenchido", type=["csv"])
if uploaded_file is not None:
    df_notas = pd.read_csv(uploaded_file)
    st.write("📋 **Notas Carregadas:**")
    st.dataframe(df_notas)
