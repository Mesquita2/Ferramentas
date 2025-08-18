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
    ARQUIVOBASE = "alunosxdisciplinas_geral"

    def gerar_relatorio_assinatura(df_alunos, curso, periodo, turma, data_hoje, imagem_cabecalho, imagem_rodape):
        data_hoje = data_hoje.strftime("%d/%m/%Y")
        df_sorted = df_alunos.sort_values(by=["ALUNO"]).reset_index(drop=True)

        doc = Document()
        section = doc.sections[0]
        section.left_margin = Inches(0.5)
        section.right_margin = Inches(0.5)
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)

        # Cabeçalho
        header = section.header
        header_paragraph = header.paragraphs[0]
        header_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = header_paragraph.add_run()
        if os.path.exists(imagem_cabecalho):
            run.add_picture(imagem_cabecalho, width=Inches(8))

        # Rodapé
        footer = section.footer
        footer_paragraph = footer.paragraphs[0]
        footer_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_footer = footer_paragraph.add_run()
        if os.path.exists(imagem_rodape):
            run_footer.add_picture(imagem_rodape, width=Inches(8))

        # Info turma
        if curso: doc.add_paragraph(f"Curso: {curso}", style='Heading 2')
        if turma: doc.add_paragraph(f"Turma: {turma}")
        if periodo: doc.add_paragraph(f"Período: {periodo}")
        doc.add_paragraph(f"Data: {data_hoje}")
        doc.add_paragraph(" ")

        # Tabela
        tabela = doc.add_table(rows=1, cols=4)
        tabela.style = "Table Grid"
        hdr_cells = tabela.rows[0].cells
        hdr_cells[0].text = 'Aluno'
        hdr_cells[1].text = 'RA'
        hdr_cells[2].text = 'E-mail'
        hdr_cells[3].text = 'Assinatura'

        for _, row in df_sorted.iterrows():
            linha = tabela.add_row().cells
            linha[0].text = str(row.get("ALUNO", ""))[:200]
            linha[1].text = str(row.get("RA", ""))
            linha[2].text = str(row.get("EMAIL", ""))
            linha[3].text = " "

        output = io.BytesIO()
        doc.save(output)
        output.seek(0)
        return output

    st.title("Upload do Arquivo de Nivelamento de Inglês")
    uploaded_file = st.file_uploader("Selecione o arquivo (Excel ou CSV)", type=["xlsx", "csv"])
    if not uploaded_file:
        st.info("Envie um arquivo para começar.")
        return

    # Carrega arquivo enviado
    if uploaded_file.name.endswith(".xlsx"):
        df_env = pd.read_excel(uploaded_file)
    else:
        try:
            df_env = pd.read_csv(uploaded_file, sep=";")
        except Exception:
            df_env = pd.read_csv(uploaded_file, sep=",")

    # Padroniza colunas
    df_env.rename(columns={
        'Curso': 'CURSO', 'Nome completo': 'ALUNO', 'Nome': 'ALUNO',
        'Período atual': 'PERIODO', 'Período': 'PERIODO',
        'E-mail institucional': 'EMAIL', 'E-mail': 'EMAIL',
        'Email': 'EMAIL', 'email': 'EMAIL', 'RA': 'RA', 'Turma': 'TURMA'
    }, inplace=True, errors="ignore")

    for col in ['EMAIL','PERIODO']:
        if col not in df_env.columns: df_env[col] = ''

    df_env = df_env[df_env['EMAIL'].notna() & (df_env['EMAIL'] != '')].copy()

    # Base do session_state
    df_base = None
    if "dados" in st.session_state and isinstance(st.session_state["dados"], dict):
        df_base = st.session_state["dados"].get(ARQUIVOBASE)
    if df_base is None:
        df_base = st.session_state.get(ARQUIVOBASE)
    if df_base is None:
        st.error("Não encontrei o ARQUIVOBASE no st.session_state.")
        return

    # Padroniza base
    df_base = df_base.copy()
    df_base.rename(columns={
        'Curso': 'CURSO','Aluno': 'ALUNO','Nome completo': 'ALUNO',
        'Período atual': 'PERIODO','Período': 'PERIODO',
        'E-mail institucional': 'EMAIL','E-mail': 'EMAIL','Email': 'EMAIL','email': 'EMAIL',
        'RA': 'RA','Turma': 'TURMA'
    }, inplace=True, errors="ignore")

    if 'RA' in df_base.columns:
        df_base["RA"] = df_base["RA"].astype(str).str.zfill(7)
    for col in ['ALUNO', 'RA', 'CURSO', 'EMAIL', 'TURMA', 'PERIODO']:
        if col not in df_base.columns: df_base[col] = ''
    df_base = df_base[['ALUNO','RA','CURSO','EMAIL','TURMA','PERIODO']].copy()

    # Atualiza periodo pelo arquivo enviado
    df_base = df_base.merge(df_env[['EMAIL','PERIODO']].drop_duplicates(subset=['EMAIL']),
                            on='EMAIL', how='left', suffixes=('','_env'))
    if 'PERIODO_env' in df_base.columns:
        df_base['PERIODO'] = df_base['PERIODO_env'].fillna(df_base['PERIODO'])
        df_base.drop(columns=['PERIODO_env'], inplace=True)

    # Cruzamento por EMAIL
    df_cruzado = df_base[df_base['EMAIL'].isin(df_env['EMAIL'])].copy()
    df_nao_encontrados = df_env[~df_env['EMAIL'].isin(df_base['EMAIL'])].copy()

    # --- Se houver alunos encontrados ---
    if not df_cruzado.empty:
        st.subheader("Alunos encontrados no ARQUIVOBASE")
        st.dataframe(df_cruzado[['ALUNO','RA','EMAIL','CURSO','TURMA','PERIODO']])

        periodo = df_cruzado['PERIODO'].dropna().unique().tolist()
        periodo_sel = None
        if periodo:
            periodo_sel = st.selectbox("Selecione a Turma/Período", ["Todos os Periodos"] + sorted(periodo))
            if periodo_sel == "Todos os Periodos": periodo_sel = None

        df_para_relatorio = df_cruzado.copy()
        if periodo_sel: df_para_relatorio = df_para_relatorio[df_para_relatorio['PERIODO'] == periodo_sel]

        curso_head = df_para_relatorio['CURSO'].dropna().unique().tolist()
        curso_head = curso_head[0] if curso_head else ''
        periodo_head = ", ".join(df_para_relatorio['PERIODO'].dropna().unique().tolist())

        # Botão DOCX
        if st.button("Gerar relatório .docx desta Turma"):
            relatorio_docx = gerar_relatorio_assinatura(
                df_para_relatorio, curso_head, periodo_head,
                turma=(periodo_sel if periodo_sel else ''),
                data_hoje=date.today(),
                imagem_cabecalho=imagem_cabecalho,
                imagem_rodape=imagem_rodape
            )
            st.download_button(
                label="Download Relatório (.docx)",
                data=relatorio_docx,
                file_name=f"Relatorio_Assinaturas_{curso_head}_{periodo_sel or 'todas'}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

    # --- Se houver alunos não encontrados ---
    if not df_nao_encontrados.empty:
        st.subheader("Alunos **não encontrados**")
        st.dataframe(df_nao_encontrados[['ALUNO','EMAIL','CURSO','PERIODO']])

        if st.button("Gerar relatório .docx dos não encontrados"):
            relatorio_nao_encontrados = gerar_relatorio_assinatura(
                df_nao_encontrados, curso='-', periodo='-', turma='-',
                data_hoje=date.today(),
                imagem_cabecalho=imagem_cabecalho,
                imagem_rodape=imagem_rodape
            )
            st.download_button(
                label="Download Relatório Não Encontrados (.docx)",
                data=relatorio_nao_encontrados,
                file_name="Relatorio_Assinaturas_Nao_Encontrados.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

    # --- Excel completo com 2 abas ---
    if not df_cruzado.empty or not df_nao_encontrados.empty:
        output_excel_completo = io.BytesIO()
        with pd.ExcelWriter(output_excel_completo, engine='xlsxwriter') as writer:
            if not df_cruzado.empty:
                df_para_relatorio.to_excel(writer, sheet_name='Encontrados', index=False)
            if not df_nao_encontrados.empty:
                df_nao_encontrados.to_excel(writer, sheet_name='Nao_Encontrados', index=False)
            writer.save()
        output_excel_completo.seek(0)
        st.download_button(
            label="Download Excel Completo (Encontrados + Não Encontrados)",
            data=output_excel_completo,
            file_name=f"Relatorio_Completo_{curso_head}_{periodo_sel or 'todas'}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
