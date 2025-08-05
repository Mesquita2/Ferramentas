import pandas as pd
import streamlit as st
import numpy as np

def carregar():
    df = st.session_state["dados"]["dashnotas"]
    st.title("Painel de Análise de Notas")
    st.caption("Visualize a distribuição das notas por curso, disciplina e avaliação.")
    
    col_avaliacoes = ['E01','P1', 'RECP1', 'QUIZZ1','E02', 'P2', 'RECP2', 'QUIZZ2', 'P3', 'RECP3', 'RECF']

    if {"CURSO", "NOMEDISC", "CODPERLET", "P1"}.issubset(df.columns):

        df["CODPERLET"] = df["CODPERLET"].astype(str)

        # 🔽 Período letivo selecionado
        periodos = sorted(df["CODPERLET"].dropna().unique())
        periodo_sel = st.multiselect("Selecione o Período Letivo", periodos)
        
        df = df[df["CODPERLET"].isin(periodo_sel)]


        cursos = sorted(df["CURSO"].dropna().unique())
        subtabs = st.tabs(cursos + ["Total"])

        for i, curso in enumerate(cursos):
            with subtabs[i]:
                st.markdown(f"### {curso}")
                df_curso = df[df["CURSO"] == curso]

                disciplinas = sorted(df_curso["NOMEDISC"].dropna().unique())
                disciplina_sel = st.selectbox("Selecione a disciplina", disciplinas, key=f"disc_{curso}")
                avaliacao_sel = st.selectbox("Selecione a avaliação", col_avaliacoes, key=f"aval_{curso}")

                df_filtrado = df_curso[df_curso["NOMEDISC"] == disciplina_sel]
                notas = df_filtrado[avaliacao_sel].dropna()
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("**Quantidade de Alunos**", notas.count())
                col2.metric("**Média**", f"{notas.mean():.2f}")
                col3.metric("**Mediana**", f"{notas.median():.2f}")
                col4.metric("**Desvio Padrão**", f"{notas.std():.2f}")
                st.bar_chart(notas.value_counts().sort_index())
                
                st.markdown("#### Resumo por Período Letivo")
                # Filtra o DataFrame para a disciplina selecionada
                df_filtrado = df_curso[df_curso["NOMEDISC"] == disciplina_sel]
                resumo = (
                    df_filtrado.groupby("CODPERLET")[avaliacao_sel]
                    .agg(['count', 'mean', 'median', 'std'])
                    .rename(columns={
                        "count": "Quantidade de Alunos",
                        "mean": "Média",
                        "median": "Mediana",
                        "std": "Desvio Padrão"
                    })
                    .dropna()
                )

                st.dataframe(resumo.style.format({
                    "Média": "{:.2f}",
                    "Mediana": "{:.2f}",
                    "Desvio Padrão": "{:.2f}"
                }))

        if len(periodo_sel) == 0:
            st.warning("Selecione pelo menos um período letivo.")
            st.stop()

        if notas.empty:
            st.info("Não há notas disponíveis para esta seleção.")
            st.stop()    

        with subtabs[-1]:
            st.markdown("### Total (Todos os Cursos)")

            avaliacao_sel = st.selectbox("Selecione a avaliação", col_avaliacoes, key="aval_total")

            # Coletar todas as notas dessa avaliação, ignorando disciplina
            notas = df[avaliacao_sel].dropna()

            st.write(f"**Quantidade de Alunos:** {notas.count()}")
            st.write(f"**Média:** {notas.mean():.2f}")
            st.write(f"**Mediana:** {notas.median():.2f}")
            st.write(f"**Desvio Padrão:** {notas.std():.2f}")

            st.bar_chart(notas.value_counts().sort_index())

    else:
        st.warning("A base não contém as colunas esperadas: 'CURSO', 'NOMEDISC', 'CODPERLET' e colunas de avaliação.")
