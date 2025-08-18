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
        """
        Gera um .docx contendo uma tabela para assinaturas da turma.
        A tabela terá colunas: Aluno | RA | E-mail | Assinatura
        Cabeçalho inclui Curso e Período (vindos do arquivo enviado).
        """
        data_hoje = data_hoje.strftime("%d/%m/%Y")
        df_sorted = df_alunos.sort_values(by=["ALUNO"]).reset_index(drop=True)

        doc = Document()

        # Definições de margem
        section = doc.sections[0]
        section.left_margin = Inches(0.5)
        section.right_margin = Inches(0.5)
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)

        # Cabeçalho centralizado com imagem
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

        # Título / info da turma
        if curso:
            doc.add_paragraph(f"Curso: {curso}", style='Heading 2')
        if turma:
            doc.add_paragraph(f"Turma: {turma}")
        if periodo:
            doc.add_paragraph(f"Período: {periodo}")
        doc.add_paragraph(f"Data: {data_hoje}")
        doc.add_paragraph(" ")

        # Tabela: Aluno | RA | E-mail | Assinatura
        tabela = doc.add_table(rows=1, cols=4)
        tabela.style = "Table Grid"
        tabela.autofit = True

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

    # --- carrega arquivo enviado pelo usuário ---
    if uploaded_file.name.endswith(".xlsx"):
        df_env = pd.read_excel(uploaded_file)
    else:
        try:
            df_env = pd.read_csv(uploaded_file, sep=";")
        except Exception:
            df_env = pd.read_csv(uploaded_file, sep=",")

    # padroniza colunas do arquivo enviado
    df_env.rename(columns={
        'Curso': 'CURSO',
        'Nome completo': 'ALUNO',
        'Nome': 'ALUNO',
        'Período atual': 'PERIODO',
        'Período': 'PERIODO',
        'E-mail institucional': 'EMAIL',
        'E-mail': 'EMAIL',
        'Email': 'EMAIL',
        'email': 'EMAIL',
        'RA': 'RA',
        'Turma': 'TURMA'
    }, inplace=True, errors="ignore")

    # garante colunas obrigatórias
    if 'EMAIL' not in df_env.columns:
        df_env['EMAIL'] = ''
    if 'PERIODO' not in df_env.columns:
        df_env['PERIODO'] = ''

    # remove linhas sem EMAIL
    df_env = df_env[df_env['EMAIL'].notna() & (df_env['EMAIL'] != '')].copy()

    # --- pega o ARQUIVOBASE do session_state ---
    df_base = None
    if "dados" in st.session_state and isinstance(st.session_state["dados"], dict):
        df_base = st.session_state["dados"].get(ARQUIVOBASE)
    if df_base is None:
        df_base = st.session_state.get(ARQUIVOBASE)

    if df_base is None:
        st.error("Não encontrei o ARQUIVOBASE no st.session_state. Verifique a chave 'dados' ou o nome do ARQUIVOBASE.")
        return

    # padroniza colunas do arquivo base
    df_base = df_base.copy()
    df_base.rename(columns={
        'Curso': 'CURSO',
        'Aluno': 'ALUNO',
        'Nome completo': 'ALUNO',
        'Período atual': 'PERIODO',
        'Período': 'PERIODO',
        'E-mail institucional': 'EMAIL',
        'E-mail': 'EMAIL',
        'Email': 'EMAIL',
        'email': 'EMAIL',
        'RA': 'RA',
        'Turma': 'TURMA'
    }, inplace=True, errors="ignore")

    # zfill RA
    if 'RA' in df_base.columns:
        df_base["RA"] = df_base["RA"].astype(str).str.zfill(7)

    # garante colunas mínimas existam
    for col in ['ALUNO', 'RA', 'CURSO', 'EMAIL', 'TURMA', 'PERIODO']:
        if col not in df_base.columns:
            df_base[col] = ''

    # mantém só as colunas que interessam
    base_cols = ['ALUNO', 'RA', 'CURSO', 'EMAIL', 'TURMA', 'PERIODO']
    df_base = df_base[base_cols].copy()

    # sobrescreve PERIODO do base com o enviado, pelo EMAIL
    df_base = df_base.merge(df_env[['EMAIL', 'PERIODO']].drop_duplicates(subset=['EMAIL']),
                            on='EMAIL', how='left', suffixes=('', '_env'))
    if 'PERIODO_env' in df_base.columns:
        df_base['PERIODO'] = df_base['PERIODO_env'].fillna(df_base['PERIODO'])
        df_base.drop(columns=['PERIODO_env'], inplace=True)

    # --- cruzamento por EMAIL ---
    df_cruzado = df_base[df_base['EMAIL'].isin(df_env['EMAIL'])].copy()

    if not df_cruzado.empty:
        st.subheader("Alunos encontrados no ARQUIVOBASE pelo e-mail")
        st.dataframe(df_cruzado[['ALUNO', 'RA', 'EMAIL', 'CURSO', 'TURMA', 'PERIODO']].reset_index(drop=True))

        # --- seleção de Turma para gerar relatório ---
        periodo = df_cruzado['PERIODO'].dropna().unique().tolist()
        if not periodo:
            periodo_sel = None
        else:
            periodo_sel = st.selectbox("Selecione a Turma para gerar relatório", ["Todos os Periodos"] + sorted(periodo))
            if periodo_sel == "Todos os Periodos":
                periodo_sel = None

        df_para_relatorio = df_cruzado.copy()
        if periodo_sel:
            df_para_relatorio = df_para_relatorio[df_para_relatorio['PERIODO'] == periodo_sel]

        st.write(f"Alunos que irão para o relatório: {len(df_para_relatorio)}")
        st.dataframe(df_para_relatorio[['ALUNO', 'RA', 'EMAIL', 'CURSO', 'TURMA', 'PERIODO']].reset_index(drop=True))

        # cabeçalho
        curso_exib = df_para_relatorio['CURSO'].dropna().unique().tolist()
        curso_head = curso_exib[0] if curso_exib else ''
        periodo_vals = df_para_relatorio['PERIODO'].dropna().unique().tolist()
        periodo_head = ", ".join(map(str, periodo_vals)) if periodo_vals else ''

        if st.button("Gerar relatório .docx desta Turma"):
            relatorio_docx = gerar_relatorio_assinatura(
                df_para_relatorio,
                curso=curso_head,
                periodo=periodo_head,
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

    # --- alunos não encontrados ---
    df_nao_encontrados = df_env[~df_env['EMAIL'].isin(df_base['EMAIL'])].copy()

    if not df_nao_encontrados.empty:
        st.subheader("Alunos **não encontrados** no ARQUIVOBASE")
        st.dataframe(df_nao_encontrados[['ALUNO', 'EMAIL', 'CURSO', 'PERIODO']].reset_index(drop=True))

        if st.button("Gerar relatório .docx dos e-mails não encontrados"):
            relatorio_nao_encontrados = gerar_relatorio_assinatura(
                df_nao_encontrados,
                curso='-',
                periodo='-',
                turma='-',
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
            
        # --- Relatório Excel dos alunos encontrados ---
        if not df_cruzado.empty:
            output_excel = io.BytesIO()
            df_para_relatorio.to_excel(output_excel, index=False)
            output_excel.seek(0)

            st.download_button(
                label="Download Excel - Alunos Encontrados",
                data=output_excel,
                file_name=f"Alunos_Encontrados_{curso_head}_{periodo_sel or 'todas'}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        # --- Relatório Excel dos alunos não encontrados ---
        if not df_nao_encontrados.empty:
            output_excel_nao = io.BytesIO()
            df_nao_encontrados.to_excel(output_excel_nao, index=False)
            output_excel_nao.seek(0)

            st.download_button(
                label="Download Excel - Alunos Não Encontrados te et",
                data=output_excel_nao,
                file_name="Alunos_Nao_Encontrados.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
