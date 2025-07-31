from datetime import date
import os
from docx import Document
from docx.shared import Pt, RGBColor, Inches
import streamlit as st
import pandas as pd
import io
from auth import check_authentication

imagem_rodape = "Endereço.jpeg"
imagem_cabecalho = 'Logo.jpg'    
ARQUIVOBASE = "alunosxdisciplinas"
ARQUIVOREC = "rec_simulado"

def carregar():
    
    # Função para substituir o arquivo de alunos
    def limpar_rec(df):
        if df is None:
            st.warning("Não existe arquivo REC, volte à página Inicial!")
            return pd.DataFrame()

        df_base = st.session_state["dados"].get(ARQUIVOBASE).copy()
        
        # Padroniza RA
        df["RA"] = df["RA"].astype(str).str.zfill(7)
        df_base["RA"] = df_base["RA"].astype(str).str.zfill(7)
        
        # Renomeia NOME → ALUNO
        df.rename(columns={'NOME': 'ALUNO'}, inplace=True)
        
        # Remove duplicados e cancelados
        df = df.drop_duplicates(subset=['RA'])
        df = df[df['CODSTATUS'] != 'C']
        
        st.success("Dados de alunos substituídos com sucesso!")
        return df

    def adicionar_imagem_no_cabecalho(doc, imagem_cabecalho):
        section = doc.sections[0]
        header = section.header
        paragraph = header.paragraphs[0]
        section.header_distance = Inches(0.2)
        run = paragraph.add_run()
        run.add_picture(imagem_cabecalho, width=Inches(7.5), height=Inches(1))

    def adicionar_imagem_no_rodape(doc, imagem_rodape):
        section = doc.sections[0]
        footer = section.footer
        paragraph = footer.paragraphs[0]
        section.footer_distance = Inches(0.2)
        run = paragraph.add_run()
        run.add_picture(imagem_rodape, width=Inches(7.5), height=Inches(1))

    def gerar_relatorio(df_filtrado):
        df = df_filtrado.copy()
        dataatual = date.today().strftime('%d/%m/%Y')
        
        doc = Document()
        adicionar_imagem_no_cabecalho(doc, imagem_cabecalho)
        adicionar_imagem_no_rodape(doc, imagem_rodape)
        
        # Margens estreitas
        sec = doc.sections[0]
        for side in ("left", "right", "top", "bottom"):
            setattr(sec, f"{side}_margin", Inches(0.5))
        
        # Título
        p = doc.add_paragraph()
        run = p.add_run("\n\nSIMULADO DE RECUPERAÇÃO")
        run.font.name = 'Arial'; run.font.size = Pt(14); run.font.color.rgb = RGBColor(0, 0, 0)
        
        # Turma e data
        for text in (f"Turma: {turma}", f"Data: {dataatual}"):
            p = doc.add_paragraph()
            run = p.add_run(text); run.font.name = 'Arial'; run.font.size = Pt(12)

        # Tabela apenas ALUNO + ASSINATURA
        tabela = doc.add_table(rows=1, cols=2)
        tabela.style = 'Table Grid'
        hdr = tabela.rows[0].cells
        hdr[0].text = 'ALUNO'; hdr[1].text = 'ASSINATURA'
        
        for _, row in df[['ALUNO']].iterrows():
            cells = tabela.add_row().cells
            cells[0].text = str(row['ALUNO'])
            cells[1].text = ''

        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)
        return buf

    def gerar_excel(df_filtrado):
        df = df_filtrado.copy()
        df['RA'] = df['RA'].astype(str)
        df['NOTAS'] = 0
        df = df[['CODTURMA', 'RA', 'ALUNO', 'NOTAS']].sort_values('ALUNO')
        
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name="Notas")
        out.seek(0)
        return out

    # Interface
    st.title("Limpeza e tratamento de notas de REC")
    df_cadastro = st.session_state["dados"].get(ARQUIVOREC)
    if df_cadastro is not None:
        st.subheader("Dados dos Cadastrados na REC")
        st.dataframe(df_cadastro[['CODTURMA', 'NOME']])
    else:
        st.warning("Nenhum dado de REC carregado!")
        st.stop()

    df_rec = limpar_rec(df_cadastro.copy())
    if df_rec.empty:
        st.stop()

    turmas = df_rec["CODTURMA"].unique().tolist()
    turma = st.selectbox("Escolha a turma", turmas)
    prova = st.selectbox("Escolha se é REC_P3", ["REC_P3"])

    df_filtrado = df_rec[df_rec["CODTURMA"] == turma].copy()
    
    df_filtrado = df_filtrado.sort_values(by="ALUNO")
    total = df_filtrado["ALUNO"].count()

    st.markdown(f"**Alunos da Turma: {turma}**")
    st.markdown(f"**Quantidade de REC solicitadas: {total}**")
    st.dataframe(df_filtrado[["ALUNO"]])

    # Botões de download
    excel = gerar_excel(df_filtrado)
    st.download_button(
        "⬇ Gerar e Baixar Planilha Excel",
        data=excel,
        file_name=f"{turma}_{prova}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
            
    rel = gerar_relatorio(df_filtrado)
    st.download_button(
        "⬇ Gerar e Baixar Relatório de Assinaturas",
        data=rel,
        file_name=f"{turma}_{prova}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
