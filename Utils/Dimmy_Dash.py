import pandas as pd
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

@st.cache_data
def carregar_dados():
    return st.session_state['dados']['dashnotas']


def calcular_metricas(notas):
    return {
        'Quantidade de Alunos': notas.count(),
        'Média': notas.mean(),
        'Mediana': notas.median(),
        'Desvio Padrão': notas.std()
    }


def get_avaliacoes_por_grupo(grupo: str) -> list[str]:
    if grupo == 'P1':
        return ['Média P1', 'P1', 'RECP1', 'QUIZZ1']
    elif grupo == 'P2':
        return ['Média P2', 'P2', 'RECP2', 'QUIZZ2']
    elif grupo == 'P3':
        return ['P3', 'RECP3']
    else:
        return ['Média Final', 'REC Final']


def carregar():
    df = carregar_dados()
    if df.empty:
        st.error('Nenhum dado disponível para os filtros aplicados.')
        st.stop()

    st.title('Painel de Análise de Notas')
    st.caption('Visualize a distribuição das notas por curso, disciplina e avaliação.')

    df.rename(columns={
        'E01': 'Média P1',
        'E02': 'Média P2',
        'MF': 'Média Final',
        'RECF': 'REC Final'
    }, inplace=True)

    df['CODPERLET'] = df['CODPERLET'].astype(str)
    periodos = sorted(df['CODPERLET'].dropna().unique())
    periodo_sel = st.multiselect('Selecione o Período Letivo', periodos)
    if not periodo_sel:
        st.warning('Selecione pelo menos um período letivo.')
        st.stop()
    df = df[df['CODPERLET'].isin(periodo_sel)]

    cursos = sorted(df['CURSO'].dropna().unique())
    subtabs = st.tabs(cursos + ['Total'])

    for i, curso in enumerate(cursos):
        with subtabs[i]:
            st.markdown(f'### {curso}')
            df_curso = (
                df[df['CURSO'] == curso]
                .drop_duplicates(subset=['ALUNO', 'NOMEDISC'])
            )

            disciplinas = sorted(df_curso['NOMEDISC'].dropna().unique())
            disciplina_sel = st.selectbox('Selecione a disciplina', disciplinas, key=f'disc_{curso}')

            grupo = st.selectbox('Selecione o grupo de avaliação', ['P1', 'P2', 'P3', 'Final'], key=f'grupo_{curso}')
            avals = get_avaliacoes_por_grupo(grupo)
            avaliacao_sel = st.selectbox('Selecione a avaliação', avals, key=f'aval_{curso}')

            df_filtrado = df_curso[df_curso['NOMEDISC'] == disciplina_sel]
            notas = df_filtrado[avaliacao_sel].dropna()

            # Top 5 por turma
            with st.expander('Top 5 Alunos por Turma'):
                turmas = sorted(df_filtrado['CODTURMA'].dropna().unique())
                if turmas:
                    turma_sel = st.selectbox('Selecione a Turma', turmas, key=f'turma_{curso}')
                    df_turma = df_filtrado[df_filtrado['CODTURMA'] == turma_sel]
                    top5_turma = (
                        df_turma[['RA', 'ALUNO', avaliacao_sel]]
                        .dropna()
                        .sort_values(by=avaliacao_sel, ascending=False)
                        .head(5)
                    )
                    st.dataframe(top5_turma.style.format({avaliacao_sel: '{:.2f}'}))
                else:
                    st.info('Nenhuma turma disponível para esta disciplina.')

            # Top 3 da disciplina
            with st.expander(f'Top 3 {avaliacao_sel} na disciplina'):
                if avaliacao_sel in df_filtrado.columns:
                    top3 = (
                        df_filtrado[['RA', 'ALUNO', avaliacao_sel]]
                        .dropna()
                        .sort_values(by=avaliacao_sel, ascending=False)
                        .head(3)
                    )
                    st.dataframe(top3.style.format({avaliacao_sel: '{:.2f}'}))
                else:
                    st.info(f"Coluna '{avaliacao_sel}' não disponível.")

            metricas = calcular_metricas(notas)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric('Qtd Alunos', metricas['Quantidade de Alunos'])
            c2.metric('Média', f"{metricas['Média']:.2f}")
            c3.metric('Mediana', f"{metricas['Mediana']:.2f}")
            c4.metric('Desvio Padrão', f"{metricas['Desvio Padrão']:.2f}")
            st.bar_chart(notas.value_counts().sort_index())

            resumo = (
                df_filtrado.groupby('CODPERLET')[avaliacao_sel]
                .agg(['count', 'mean', 'median', 'std'])
                .rename(columns={'count': 'Qtd Alunos', 'mean': 'Média', 'median': 'Mediana', 'std': 'Desvio Padrão'})
                .dropna()
            )
            st.dataframe(resumo.style.format({'Média': '{:.2f}', 'Mediana': '{:.2f}', 'Desvio Padrão': '{:.2f}'}))

            with st.expander('Análise de Máxima por Disciplina'):
                st.markdown('### Máximas por Disciplina')
                grupo_max = st.selectbox('Selecione o grupo de avaliação', ['P1', 'P2', 'P3', 'Final'], key=f'grupo_max_{curso}')
                avals_max = get_avaliacoes_por_grupo(grupo_max)
                col_aval = st.selectbox('Selecione a avaliação para análise', avals_max, key=f'aval_max_{curso}')

                resumo_disc = (
                    df_curso.groupby('NOMEDISC')[col_aval]
                    .agg(['max', 'mean', 'median'])
                    .rename(columns={'max': 'Maior Nota', 'mean': 'Média', 'median': 'Mediana'})
                    .dropna()
                )
                resumo_disc['Diferença (Máx - Média)'] = resumo_disc['Maior Nota'] - resumo_disc['Média']
                resumo_disc = resumo_disc.sort_values(by='Maior Nota', ascending=False)
                st.dataframe(resumo_disc.style.format({'Maior Nota': '{:.2f}', 'Média': '{:.2f}', 'Mediana': '{:.2f}', 'Diferença (Máx - Média)': '{:.2f}'}))
            
            with st.expander('Top 5 Médias Finais por Turma (Todas as Disciplinas)'):
                turmas_mf = sorted(df_curso['CODTURMA'].dropna().unique())
                if turmas_mf:
                    turma_mf_sel = st.selectbox('Selecione a Turma', turmas_mf, key=f'top5mf_turma_{curso}')
                    df_turma_mf = df_curso[df_curso['CODTURMA'] == turma_mf_sel]
                    df_turma_mf = df_turma_mf.drop_duplicates(subset=['ALUNO', 'NOMEDISC'])
                    top5_mf = (
                        df_turma_mf.groupby(['RA', 'ALUNO'])['Média Final']
                        .mean()
                        .reset_index()
                        .rename(columns={'Média Final': 'Média Geral'})
                        .sort_values(by='Média Geral', ascending=False)
                        .head(5)
                    )
                    st.dataframe(top5_mf.style.format({'Média Geral': '{:.2f}'}))
                else:
                    st.info('Nenhuma turma disponível para Média Final.')

    # Aba Total
    with subtabs[-1]:
        st.markdown('### Total (Todos os Cursos)')
        grupo_tot = st.selectbox('Selecione o grupo de avaliação', ['P1', 'P2', 'P3', 'Final'], key='grupo_total')
        avals_tot = get_avaliacoes_por_grupo(grupo_tot)
        avaliacao_tot = st.selectbox('Selecione a avaliação', avals_tot, key='aval_total')

        notas_tot = df[avaliacao_tot].dropna()
        metricas_tot = calcular_metricas(notas_tot)
        d1, d2, d3, d4 = st.columns(4)
        d1.metric('Qtd Alunos', metricas_tot['Quantidade de Alunos'])
        d2.metric('Média', f"{metricas_tot['Média']:.2f}")
        d3.metric('Mediana', f"{metricas_tot['Mediana']:.2f}")
        d4.metric('Desvio Padrão', f"{metricas_tot['Desvio Padrão']:.2f}")
        st.bar_chart(notas_tot.value_counts().sort_index())
