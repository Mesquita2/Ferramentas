import streamlit as st
import pandas as pd
from auth import check_authentication

def carregar():
    # Pega o DataFrame geral dos alunos
    df_alunos = st.session_state["dados"].get("alunosxdisciplinas").copy()
    df_base = df_alunos.copy()


    padrao_remover = r'(?:Projeto de Extensão|Seminários|Liga dos Campeões|TCC|Estágio|Trabalho de Conclusão de Curso)'
    df_base = df_base[
        ~df_base['DISCIPLINA'].str.contains(padrao_remover, case=False, na=False) &
        df_base['TURMADISC'].astype(str).str.len().le(4)
    ].reset_index(drop=True)

    # Renomear colunas para o padrão usado nas demais páginas
    df_base.rename(columns={
        'NOMEDISCIPLINA': 'DISCIPLINA',
        'NOMECURSO': 'CURSO',
        'NOMEALUNO': 'ALUNO'
    }, inplace=True)

    # Garantir RA com 7 dígitos
    df_base['RA'] = df_base['RA'].astype(str).str.zfill(7)

    st.title("Gerar Notas Zero para Alunos Faltantes")

    # Filtros: Curso e Turma
    cursos = sorted(df_base['CURSO'].dropna().unique())
    curso_selecionado = st.selectbox("Selecione o curso:", cursos, index=None)

    if curso_selecionado:
        turmas = sorted(df_base[df_base['CURSO'] == curso_selecionado]['TURMADISC'].dropna().unique())
        turmas_selecionadas = st.multiselect("Selecione a(s) Turma(s):", turmas)

        if turmas_selecionadas:
            # Filtrar alunos dessas turmas
            df_filtrado = df_base[
                (df_base['CURSO'] == curso_selecionado) &
                (df_base['TURMADISC'].isin(turmas_selecionadas))
            ]

            # Multi-select de alunos faltantes
            alunos_disponiveis = df_filtrado[['RA', 'ALUNO']].drop_duplicates()
            alunos_disponiveis['RA_NOME'] = alunos_disponiveis['RA'] + " - " + alunos_disponiveis['ALUNO']

            alunos_selecionados = st.multiselect(
                "Selecione os alunos faltantes:",
                options=alunos_disponiveis['RA_NOME'].tolist()
            )

            ras_selecionados = [item.split(' - ')[0] for item in alunos_selecionados]

            if ras_selecionados:
                # Filtrar disciplinas disponíveis nessas turmas
                disciplinas_disponiveis = sorted(
                    df_filtrado['DISCIPLINA'].dropna().unique()
                )

                disciplinas_excluidas = st.multiselect(
                    "Disciplinas que NÃO entram na média (não aplicar nota zero para elas):",
                    options=disciplinas_disponiveis,
                    default=[]
                )

                # Filtrar apenas os alunos e disciplinas que devem receber nota zero
                df_resultado = df_filtrado[
                    (df_filtrado['RA'].isin(ras_selecionados)) &
                    (~df_filtrado['DISCIPLINA'].isin(disciplinas_excluidas))
                ].copy()

                st.success(f"{len(df_resultado)} registro(s) serão gerados com nota zero.")

                df_resultado['NOTAS'] = 0.00

                # Definições fixas de etapa e prova
                etapa = "P3"
                tipoetapa = 'N'
                codetapa = 3
                codprova = 1
                prova = st.selectbox('Tipo de prova:', ['Prova', 'Recuperação'])

                if prova == "Recuperação":
                    codprova = 2

                # Adicionar colunas fixas
                df_resultado['ETAPA'] = etapa
                df_resultado['PROVA'] = prova
                df_resultado['TIPOETAPA'] = tipoetapa
                df_resultado['CODETAPA'] = codetapa
                df_resultado['CODPROVA'] = codprova

                # Garantir todas as colunas finais
                colunas_finais = ['CODCOLIGADA', 'CURSO', 'TURMADISC', 'IDTURMADISC', 'DISCIPLINA', 
                                'RA', 'ALUNO', 'ETAPA', 'PROVA', 'TIPOETAPA', 'CODETAPA', 'CODPROVA', 'NOTAS']
                
                for col in colunas_finais:
                    if col not in df_resultado.columns:
                        df_resultado[col] = ""

                df_resultado = df_resultado[colunas_finais]

                st.subheader("Arquivo Final - Notas Zero (Faltantes)")
                st.dataframe(df_resultado)

                # Formatar RA e Nota para exportação
                df_resultado['RA'] = df_resultado['RA'].astype(str).str.zfill(7)
                df_resultado['NOTAS'] = df_resultado['NOTAS'].apply(lambda x: f"{x:.2f}".replace('.', ','))

                # Exportar como TXT
                output = df_resultado.to_csv(index=False, sep=';', encoding='utf-8', header=False)
                st.download_button(
                    label="⬇ Baixar Arquivo TXT para Importação",
                    data=output,
                    file_name=f"faltantes_{curso_selecionado}.txt",
                    mime="text/plain"
                )
