from datetime import date
import io
import pandas as pd
import streamlit as st
from docx import Document
from docx.shared import Inches
import os
from docx.enum.text import WD_ALIGN_PARAGRAPH

def carregar():
    imagem_rodape = "./Endereço.jpeg"
    imagem_cabecalho = "./Logo.jpg"

    def gerar_relatorio_assinatura(df, curso, periodo, data_hoje, imagem_cabecalho, imagem_rodape):
        data_hoje = data_hoje.strftime("%d/%m/%Y")
        df = df.sort_values(by=["ALUNO"])

        doc = Document()

        # Definições de margem
        section = doc.sections[0]
        section.left_margin = Inches(0.5)
        section.right_margin = Inches(0.5)
        section.top_margin = Inches(1)   
        section.bottom_margin = Inches(1) 

        # Cabeçalho centralizado
        header = section.header
        header_paragraph = header.paragraphs[0]  # pega o parágrafo existente
        header_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER  # centraliza o parágrafo
        run = header_paragraph.add_run()
        run.add_picture(imagem_cabecalho, width=Inches(10))  # largura da imagem

        # Rodapé centralizado
        footer = section.footer
        footer_paragraph = footer.paragraphs[0]
        footer_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_footer = footer_paragraph.add_run()
        run_footer.add_picture(imagem_rodape, width=Inches(10)))

        # Conteúdo
        doc.add_paragraph(f"Curso: {curso}", style='Heading 2')
        doc.add_paragraph(f"Período: {periodo}")
        doc.add_paragraph(f"Data: {data_hoje}")
        doc.add_paragraph(" ")

        # Tabela de assinaturas
        tabela = doc.add_table(rows=1, cols=2)
        tabela.style = "Table Grid"
        tabela.autofit = True

        hdr_cells = tabela.rows[0].cells
        hdr_cells[0].text = 'Aluno'
        hdr_cells[1].text = 'Assinatura'

        for _, row in df.iterrows():
            linha = tabela.add_row().cells
            linha[0].text = row["ALUNO"]
            linha[1].text = " "

        output = io.BytesIO()
        doc.save(output)
        output.seek(0)
        return output

    st.title("Upload do Arquivo de Nivelamento de Inglês")

    uploaded_file = st.file_uploader("Selecione o arquivo (Excel ou CSV)", type=["xlsx", "csv"])

    if uploaded_file:
        if uploaded_file.name.endswith(".xlsx"):
            df = pd.read_excel(uploaded_file)
        else:
            df = pd.read_csv(uploaded_file, sep=";")  # ajuste se necessário

        # Padroniza colunas principais
        df.rename(columns={
            'Curso': 'CURSO',
            'Nome completo': 'ALUNO',
            'Período atual': 'PERIODO'
        }, inplace=True, errors="ignore")

        st.subheader("Pré-visualização dos dados carregados")
        st.dataframe(df.head(10))

        # 🔹 Filtro por Curso
        cursos = df["CURSO"].dropna().unique().tolist()
        curso_sel = st.selectbox("Selecione o Curso", cursos)
        
        data_sel = st.date_input(
            "Selecione uma data:",
            value=date.today()
        )
        data_hoje = data_sel
    
        df_curso = df[df["CURSO"] == curso_sel]

        # 🔹 Filtro por Período
        periodos = df_curso["PERIODO"].dropna().unique().tolist()
        periodo_sel = st.selectbox("Selecione o Período", periodos)

        df_periodo = df_curso[df_curso["PERIODO"] == periodo_sel]

        st.write(f"**Curso:** {curso_sel} | **Período:** {periodo_sel}")
        st.write(f"**Total de alunos: {df_periodo['ALUNO'].nunique()}**")
        st.dataframe(df_periodo[["ALUNO"]])

        # Botão de relatório
        relatorio_docx = gerar_relatorio_assinatura(df_periodo, curso_sel, periodo_sel, data_hoje, imagem_cabecalho, imagem_rodape)
        st.download_button(
            label="Gerar Relatório para Impressão",
            data=relatorio_docx,
            file_name=f"Relatorio_Assinaturas_{curso_sel}_{periodo_sel}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
