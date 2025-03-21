import streamlit as st
import pandas as pd
import io

# Função para carregar os alunos do arquivo Excel
def carregar_alunos():
    try:
        df = pd.read_excel("alunos.xlsx")  # Agora lê do arquivo Excel
        
        # Rename Colunas
        df.rename(columns={'NOMEDISCIPLINA': 'DISCIPLINA',
                           'NOMECURSO': 'CURSO',
                           'NOMEALUNO': 'ALUNO',
                           'TURMADISC': 'TURMADISC'}, inplace=True)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo alunos.xlsx: {e}")
        return pd.DataFrame()

# Função para gerar a planilha de notas em Excel
def gerar_excel(df_alunos, disciplina, turma):
    df_filtrado = df_alunos[(df_alunos["DISCIPLINA"] == disciplina) & (df_alunos["TURMADISC"] == turma)]
    
    colunas = ['CODCOLIGADA', 'CURSO', 'TURMADISC', 'IDTURMADISC', 'DISCIPLINA', 'RA', 'ALUNO']  # Nova ordem TOTVS
    df_filtrado = df_filtrado[colunas]
    df_filtrado['RA'] = df_filtrado['RA'].astype(str)  # Seleciona apenas os nomes dos alunos
    df_filtrado["Nota"] = 0  # Coluna vazia para o professor preencher

    # Criar o arquivo Excel em memória
    output = io.BytesIO()  # Usamos BytesIO para criar um arquivo em memória
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_filtrado.to_excel(writer, index=False, sheet_name="Notas")
    output.seek(0)  # Volta para o início do arquivo para download
    return output

# Defina a configuração da página antes de qualquer outro comando do Streamlit
st.set_page_config(
    page_title="Gerenciamento de Notas",
    page_icon="📚",  # Pode ser um emoji ou caminho para um ícone
    layout="wide"  # Isso faz o layout ser mais largo
)


# Interface do Streamlit
st.title("📚 Gerador de Planilha de Notas")

# Carregar os dados dos alunos
df_alunos = carregar_alunos()
if df_alunos.empty:
    st.stop()

# Seleção de disciplina
disciplinas = df_alunos["DISCIPLINA"].unique().tolist()
# Selecione a disciplina
disciplina = st.selectbox("📖 Escolha a disciplina", disciplinas)
# Filtra as turmas com base na disciplina selecionada
turmas_filtradas = df_alunos[df_alunos["DISCIPLINA"] == disciplina]["TURMADISC"].unique().tolist()
# Selecione a turma
turma = st.selectbox("🏫 Escolha a turma", turmas_filtradas)
# Filtrar os alunos conforme a disciplina e a turma selecionadas
df_filtrado = df_alunos[(df_alunos["DISCIPLINA"] == disciplina) & (df_alunos["TURMADISC"] == turma)]
# Exibir os alunos filtrados
st.write(f"📝 **Alunos da Disciplina: {disciplina} | Turma: {turma}**")
st.dataframe(df_filtrado[["ALUNO", "DISCIPLINA", "TURMADISC"]])

# Botão para gerar e baixar a planilha Excel
if st.button("📥 Gerar Planilha Excel"):
    excel_file = gerar_excel(df_alunos, disciplina, turma)
    st.download_button(
        label="⬇ Baixar Planilha Excel",
        data=excel_file,
        file_name=f"{disciplina}_{turma}_notas.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


