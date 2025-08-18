from datetime import date
import io
import pandas as pd
import streamlit as st
from docx import Document
from docx.shared import Inches

def carregar():

    # Relatório para assinatura
    def gerar_relatorio_assinatura(df, disciplinas, turmas):
        data_hoje = date.today().strftime("%d/%m/%Y")
        df = df[
            (df["DISCIPLINA"].isin(disciplinas)) & 
            (df["TURMADISC"].isin(turmas))
        ].copy()

        df = df.sort_values(by=["DISCIPLINA", "TURMADISC", "ALUNO"])
        doc = Document()

        # Definições de margem
        section = doc.sections[0]
        section.left_margin = Inches(0.5)
        section.right_margin = Inches(0.5)
        section.top_margin = Inches(0.5)
        section.bottom_margin = Inches(0.5)

        for (disciplina, turma), grupo in df.groupby(["DISCIPLINA", "TURMADISC"]):
            doc.add_paragraph(f"Disciplina: {disciplina}", style='Heading 2')
            doc.add_paragraph(f"Turma: {turma}")
            doc.add_paragraph(f"Data: {data_hoje}")
            doc.add_paragraph(" ")

            tabela = doc.add_table(rows=1, cols=2)
            tabela.style = "Table Grid"
            tabela.autofit = True

            hdr_cells = tabela.rows[0].cells
            hdr_cells[0].text = 'Aluno'
            hdr_cells[1].text = 'Assinatura'

            for _, row in grupo.iterrows():
                linha = tabela.add_row().cells
                linha[0].text = row["ALUNO"]
                linha[1].text = " "

        output = io.BytesIO()
        doc.save(output)
        output.seek(0)
        return output

    # ----------- INTERFACE STREAMLIT -------------
    st.title("Upload do Arquivo de Nivelamento de Inglês")

    uploaded_file = st.file_uploader("Selecione o arquivo REC (Excel ou CSV)", type=["xlsx", "csv"])

    if uploaded_file:
        if uploaded_file.name.endswith(".xlsx"):
            df = pd.read_excel(uploaded_file)
        else:
            df = pd.read_csv(uploaded_file, sep=";")  # ajuste o separador se necessário

        # Padroniza colunas principais
        df.rename(columns={
            'NOMEDISCIPLINA': 'DISCIPLINA',
            'NOMECURSO': 'CURSO',
            'NOMEALUNO': 'ALUNO',
            'CODPERLET': 'PERIODO'
        }, inplace=True, errors="ignore")

        st.subheader("Pré-visualização dos dados carregados")
        st.dataframe(df.head(10))

        # 🔹 Filtro por Curso
        cursos = df["CURSO"].dropna().unique().tolist()
        curso_sel = st.selectbox("Selecione o Curso", cursos)

        df_curso = df[df["CURSO"] == curso_sel]

        # 🔹 Filtro por Período
        periodos = df_curso["PERIODO"].dropna().unique().tolist()
        periodo_sel = st.selectbox("Selecione o Período Letivo", periodos)

        df_periodo = df_curso[df_curso["PERIODO"] == periodo_sel]

        # 🔹 Filtro de disciplinas e turmas
        disciplinas = df_periodo["DISCIPLINA"].dropna().unique().tolist()
        disciplinas_sel = st.multiselect("1. Escolha as disciplinas", disciplinas)

        if disciplinas_sel:
            turmas_disp = df_periodo[df_periodo["DISCIPLINA"].isin(disciplinas_sel)]["TURMADISC"].dropna().unique().tolist()
            turmas_sel = st.multiselect("2. Escolha as turmas", turmas_disp)

            if turmas_sel:
                df_filtrado = df_periodo[
                    (df_periodo["DISCIPLINA"].isin(disciplinas_sel)) &
                    (df_periodo["TURMADISC"].isin(turmas_sel))
                ]

                st.write(f"**Curso:** {curso_sel} | **Período:** {periodo_sel}")
                st.write(f"**Disciplinas:** {disciplinas_sel} | **Turmas:** {turmas_sel}")
                st.write(f"**Total de alunos: {df_filtrado['ALUNO'].nunique()}**")
                st.dataframe(df_filtrado[["ALUNO", "DISCIPLINA", "TURMADISC"]])

                # Relatórios
                relatorio_docx = gerar_relatorio_assinatura(df_periodo, disciplinas_sel, turmas_sel)
                st.download_button(
                    label="Gerar Relatório para Impressão",
                    data=relatorio_docx,
                    file_name=f"Relatorio_Assinaturas_{curso_sel}_{periodo_sel}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
