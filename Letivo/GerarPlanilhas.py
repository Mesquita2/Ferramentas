import streamlit as st
import pandas as pd
import io


def carregar():       
    # Função para carregar os alunos do arquivo Excel
    def carregar_alunos():
        try:
            df_base = st.session_state["dados"].get("alunosxdisciplinas")
            df = df_base.copy()
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
        colunas = ['CODCOLIGADA', 'CURSO', 'TURMADISC', 'IDTURMADISC', 'DISCIPLINA', 'RA', 'ALUNO']
        df_filtrado = df_filtrado[colunas]
        df_filtrado['RA'] = df_filtrado['RA'].astype(str)
        df_filtrado["NOTAS"] = 0  # Coluna vazia para o professor preencher
        colunas = ['TURMADISC', 'DISCIPLINA', 'RA', 'ALUNO', 'NOTAS']
        df_filtrado = df_filtrado[colunas]
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_filtrado.to_excel(writer, index=False, sheet_name="Notas")
        output.seek(0)
        return output

    st.title("Gerador de Planilha de Notas")

    df_alunos = carregar_alunos()
    if df_alunos.empty:
        st.stop()

    disciplinas = df_alunos["DISCIPLINA"].unique().tolist()
    disciplina = st.selectbox("Escolha a disciplina", disciplinas)

    turmas_filtradas = df_alunos[df_alunos["DISCIPLINA"] == disciplina]["TURMADISC"].unique().tolist()
    turma = st.selectbox("Escolha a turma", turmas_filtradas)

    prova = st.selectbox("Escolha se é P1 ou P2 ou Quiz", ["P1", "P2", "Quiz P1", "Quiz P2"])

    df_filtrado = df_alunos[(df_alunos["DISCIPLINA"] == disciplina) & (df_alunos["TURMADISC"] == turma)]
    st.write(f"**Alunos da Disciplina: {disciplina} | Turma: {turma}**")
    st.dataframe(df_filtrado[["ALUNO", "DISCIPLINA", "TURMADISC"]])


    if disciplina and turma:
        excel_file = gerar_excel(df_alunos, disciplina, turma)
        st.download_button(
            label="Gerar e Baixar Planilha Excel",
            data=excel_file,
            file_name=f"{disciplina}_{turma}_{prova}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        
