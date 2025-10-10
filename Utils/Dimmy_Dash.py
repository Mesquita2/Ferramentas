import pandas as pd
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px

@st.cache_data
def carregar_dados():
    return st.session_state['dados']['dashnotas']

# === gráfico ORIGINAL de barras (mantido para 'o outro' que quer continuar igual) ===
def analise_notas_bar(notas, anos=None):
    ## Analise temporal das notas com base nas escolhas que forem passadas Ano e Nota separados por Turma 
    notas_num = pd.to_numeric(notas, errors='coerce')

    if anos is not None:
        anos = pd.Series(anos)

    if anos is not None:
        df = pd.DataFrame({'Nota': notas_num, 'Ano': anos}).dropna()
    else:
        df = pd.DataFrame({'Nota': notas_num}).dropna()

    if df.empty:
        if anos is not None:
            df_empty = pd.DataFrame({'Nota': [], 'Quantidade': [], 'Ano': []})
            fig = px.bar(df_empty, x='Nota', y='Quantidade', color='Ano')
        else:
            df_empty = pd.DataFrame({'Nota': [], 'Quantidade': []})
            fig = px.bar(df_empty, x='Nota', y='Quantidade')
        fig.update_layout(title='Distribuição de Notas', xaxis_title='Nota', yaxis_title='Quantidade')
        return fig

    if anos is not None:
        df_plot = df.groupby(['Ano', 'Nota']).size().reset_index(name='Quantidade')
        fig = px.bar(
            df_plot,
            x='Nota',
            y='Quantidade',
            color='Ano',
            barmode='group',
            color_discrete_sequence=px.colors.qualitative.Set2
        )
    else:
        contagem = df['Nota'].value_counts().sort_index()
        df_plot = pd.DataFrame({'Nota': contagem.index.astype(float), 'Quantidade': contagem.values})
        fig = px.bar(
            df_plot,
            x='Nota',
            y='Quantidade',
            color_discrete_sequence=['#5C2D91']
        )

    fig.update_layout(
        title='Distribuição de Notas por Ano' if anos is not None else 'Distribuição de Notas',
        xaxis_title='Nota',
        yaxis_title='Quantidade',
        margin=dict(t=40, b=20, l=10, r=10),
        legend_title_text='Ano' if anos is not None else None
    )
    return fig

def grafico_temporal_turma_disciplina(df, avals):
    """
    Gera gráfico temporal mostrando a média das avaliações selecionadas
    separada por Turma e Disciplina.
    
    Parâmetros:
    - df: DataFrame filtrado contendo as colunas 'CODTURMA', 'NOMEDISC', 'CODPERLET' e as avaliações.
    - avals: lista de colunas de avaliações a considerar.
    
    Retorna:
    - fig: gráfico Plotly Express
    """
    if df.empty or not avals:
        st.info("Sem dados suficientes para gerar o gráfico temporal.")
        return None

    # Agrupa por Turma, Disciplina e Período letivo e calcula a média
    df_media = (
        df[['CODTURMA', 'NOMEDISC', 'CODPERLET'] + avals]
        .groupby(['CODTURMA', 'NOMEDISC', 'CODPERLET'])
        .mean(numeric_only=True)
        .reset_index()
    )

    if df_media.empty:
        st.info("Sem dados suficientes para o gráfico temporal.")
        return None

    # Se houver várias avaliações, cria uma média geral
    if len(avals) > 1:
        df_media['Média Geral'] = df_media[avals].mean(axis=1)
        y_col = 'Média Geral'
    else:
        y_col = avals[0]

    # Cria o gráfico
    fig = px.line(
        df_media,
        x='CODPERLET',
        y=y_col,
        color='CODTURMA',            # cada turma uma linha
        line_dash='NOMEDISC',        # cada disciplina com traço diferente
        markers=True,
        title=f"Evolução da média ({', '.join(avals)}) por Turma e Disciplina"
    )

    fig.update_layout(
        xaxis_title='Período Letivo',
        yaxis_title='Média',
        margin=dict(t=40, b=20, l=10, r=10),
        xaxis=dict(tickmode='linear')
    )

    return fig


# === gráfico EM LINHA (usado apenas para TURMA) ===
def analise_notas_line(notas):
    """
    Linha inteligente:
    - se <= 11 valores únicos -> plota por valor exato (linha com markers)
    - senão -> agrupa em bins inteiros 0..10 e plota a contagem por bin (linha)
    """
    notas_num = pd.to_numeric(notas, errors='coerce').dropna()
    if notas_num.empty:
        df_empty = pd.DataFrame({'Nota': [], 'Quantidade': []})
        fig = px.line(df_empty, x='Nota', y='Quantidade', markers=True)
        fig.update_layout(title='Distribuição de Notas (linha)', xaxis_title='Nota', yaxis_title='Quantidade')
        return fig

    count_unique = len(np.unique(np.round(notas_num.values, 2)))
    if count_unique <= 11:
        contagem = notas_num.value_counts().sort_index()
        df_plot = pd.DataFrame({'Nota': contagem.index.astype(float), 'Quantidade': contagem.values})
        fig = px.line(df_plot, x='Nota', y='Quantidade', markers=True)
        fig.update_layout(title='Distribuição de Notas (linha)', xaxis_title='Nota', yaxis_title='Quantidade',
                          margin=dict(t=40, b=20, l=10, r=10))
        fig.update_xaxes(dtick=1)
        return fig

    # bins 0..10 (rótulos 0..10)
    bins = np.arange(-0.5, 10.6, 1.0)
    categorias = pd.cut(notas_num, bins=bins, labels=range(0, 11), include_lowest=True)
    contagem = categorias.value_counts().sort_index()
    df_plot = pd.DataFrame({'Nota': contagem.index.astype(int), 'Quantidade': contagem.values})
    fig = px.line(df_plot, x='Nota', y='Quantidade', markers=True)
    fig.update_layout(title='Distribuição de Notas (linha, bins 0-10)', xaxis_title='Nota (0-10)', yaxis_title='Quantidade',
                      margin=dict(t=40, b=20, l=10, r=10))
    fig.update_xaxes(tickmode='linear', dtick=1, range=[0, 10])
    return fig

def calcular_metricas(notas):
    return {
        'Quantidade de Alunos': int(notas.count()),
        'Média': float(notas.mean()) if not notas.empty else float('nan'),
        'Mediana': float(notas.median()) if not notas.empty else float('nan'),
        'Desvio Padrão': float(notas.std()) if not notas.empty else float('nan')
    }

def carregar():
    df_base = carregar_dados()
    if df_base is None or df_base.empty:
        st.error('Nenhum dado disponível para os filtros aplicados.')
        st.stop()

    st.title('Painel de Análise de Notas')
    st.caption('Visualize a distribuição das notas por curso, disciplina e avaliação.')

    # renomeações
    df = df_base.copy()
    df.rename(columns={
        'E01': 'Média P1',
        'E02': 'Média P2',
        'MF': 'Média Final',
        'RECF': 'REC Final'
    }, inplace=True)

    # período
    df['CODPERLET'] = df['CODPERLET'].astype(str)
    periodos = sorted(df['CODPERLET'].dropna().unique())
    periodos = ['Todos os Períodos'] + periodos

    periodo_sel = st.multiselect('Selecione o Período Letivo', periodos)

    # Se não selecionar nada, pega todos (exceto o 'Todos os Períodos')
    if not periodo_sel:
        periodo_sel = periodos[1:]  # ignora o "Todos os Períodos"

    # Se selecionar "Todos os Períodos", também pega todos
    if 'Todos os Períodos' in periodo_sel:
        periodo_sel = periodos[1:]

    df = df[df['CODPERLET'].isin(periodo_sel)]


    # cursos e tabs
    cursos = sorted(df['CURSO'].dropna().unique())
    if not cursos:
        st.info('Não há cursos na base..')
        st.stop()
    subtabs = st.tabs(cursos[:: -1])

    # meta cols e opções de avaliação
    meta_cols = {'RA', 'ALUNO', 'CURSO', 'CODPERLET', 'NOMEDISC', 'CODTURMA'}
    eval_options = [i for i in df.columns if i not in meta_cols]
    eval_options = sorted(eval_options)

    # --- abas por curso ---
    for i, curso in enumerate(cursos[:: -1]):
        with subtabs[i]:
            st.markdown(f'### {curso}')
            df_curso = df[df['CURSO'] == curso].copy()

            # disciplina
            disciplinas = sorted(df_curso['NOMEDISC'].dropna().unique())
            disciplinas = ['Todas as Disciplinas'] + disciplinas
            disciplina_sel = st.selectbox('Selecione a disciplina', disciplinas, key=f'disc_{curso}_{i}')

            if disciplina_sel == 'Todas as Disciplinas':
                df_filtrado = df_curso.copy()
            else:
                df_filtrado = df_curso[df_curso['NOMEDISC'] == disciplina_sel].copy()

            # turmas
            st.info("Nenhuma turma selecionada — a análise será realizada com todas as turmas do filtro atual.")
            turmas_na_disc = sorted(df_filtrado['CODTURMA'].dropna().unique())
            if turmas_na_disc:
                turmas_sel = st.multiselect(
                    'Selecione a(s) Turma(s) que ministraram a disciplina',
                    turmas_na_disc,
                    key=f'turmas_{curso}_{i}'
                )
                if turmas_sel:
                    st.success(f"Analisando {len(turmas_sel)} turma(s): {', '.join(map(str, turmas_sel))}")
                else: 
                    st.success(f"Analisando todas as turmas da disciplina: {disciplina_sel}")
            else:
                st.info('Nenhuma turma encontrada para a disciplina selecionada.')
                turmas_sel = []
                
            if turmas_sel:
                df_filtrado = df_filtrado[df_filtrado['CODTURMA'].isin(turmas_sel)].copy()

            # multiselect avaliações
            avaliaveis_no_df = [i for i in eval_options if i in df_filtrado.columns]
            
            termos_filtro = ['REC', 'QUIZ', 'P1', 'P2', 'P3', 'MÉDIA']
            
            opcoes_filtradas = [
                coluna for coluna in avaliaveis_no_df
                if any(termo in coluna.upper() for termo in termos_filtro)
            ]
            
            avaliacao_sel = st.multiselect(
                'Selecione uma ou mais  avaliação(ões)',
                opcoes_filtradas,
                key=f'avals_{curso}_{i}'
            )

            if not avaliacao_sel:
                st.warning('Selecione ao menos uma avaliação para visualizar métricas/gráficos nesta aba.')
                continue

            avals_existentes = [i for i in avaliacao_sel if i in df_filtrado.columns]
            if not avals_existentes:
                st.info("As avaliações selecionadas não estão presentes no conjunto filtrado.")
                continue

            # converter para numérico
            for col in avals_existentes:
                df_filtrado[col] = pd.to_numeric(df_filtrado[col], errors='coerce')

            notas_empilhadas = df_filtrado[avals_existentes].stack().dropna()

            # top lists (média se várias avaliações)
            if len(avals_existentes) == 1:
                col_top = avals_existentes[0]
                notas_para_metricas = df_filtrado[col_top].dropna()
            else:
                df_top = df_filtrado[['RA', 'ALUNO'] + avals_existentes].copy()
                df_top['MEDIA_SEL'] = df_top[avals_existentes].mean(axis=1, skipna=True)
                col_top = 'MEDIA_SEL'
                notas_para_metricas = df_top['MEDIA_SEL'].dropna()


            # Top 5 por turma
            with st.expander('Top 5 Alunos por Turma'):
                turmas_na_disc = sorted(df_filtrado['CODTURMA'].dropna().unique())
                if turmas_na_disc:
                    turma_sel = st.selectbox('Selecione a Turma (para Top5)', turmas_na_disc, key=f'top5turma_{curso}_{i}')
                    df_turma = df_filtrado[df_filtrado['CODTURMA'] == turma_sel].copy()
                    if len(avals_existentes) == 1:
                        top5_turma = (
                            df_turma[['RA', 'ALUNO', col_top]]
                            .dropna(subset=[col_top])
                            .sort_values(by=col_top, ascending=False)
                            .head(5)
                        )
                    else:
                        df_turma_top = df_turma[['RA', 'ALUNO'] + avals_existentes].copy()
                        df_turma_top['MEDIA_SEL'] = df_turma_top[avals_existentes].mean(axis=1, skipna=True)
                        top5_turma = (
                            df_turma_top[['RA', 'ALUNO', 'MEDIA_SEL']]
                            .dropna(subset=['MEDIA_SEL'])
                            .sort_values(by='MEDIA_SEL', ascending=False)
                            .head(5)
                        )
                    if not top5_turma.empty:
                        st.dataframe(top5_turma.style.format({top5_turma.columns[-1]: '{:.2f}'}))
                    else:
                        st.info("Sem registros para o Top 5 na turma selecionada.")
                else:
                    st.info('Nenhuma turma disponível para esta disciplina/filtragem.')

            # Top 3
            with st.expander(f'Top 3 ({", ".join(avals_existentes)})'):
                if not notas_para_metricas.empty:
                    if len(avals_existentes) == 1:
                        top3 = (
                            df_filtrado[['RA', 'ALUNO', col_top]]
                            .dropna(subset=[col_top])
                            .sort_values(by=col_top, ascending=False)
                            .head(3)
                        )
                    else:
                        df_top_all = df_filtrado[['RA', 'ALUNO'] + avals_existentes].copy()
                        df_top_all['MEDIA_SEL'] = df_top_all[avals_existentes].mean(axis=1, skipna=True)
                        top3 = (
                            df_top_all[['RA', 'ALUNO', 'MEDIA_SEL']]
                            .dropna(subset=['MEDIA_SEL'])
                            .sort_values(by='MEDIA_SEL', ascending=False)
                            .head(3)
                        )
                    if not top3.empty:
                        st.dataframe(top3.style.format({top3.columns[-1]: '{:.2f}'}))
                    else:
                        st.info("Não há notas suficientes para apresentar o Top 3.")
                else:
                    st.info("Não há notas suficientes para apresentar o Top 3.")

            # Métricas e DISTRIBUIÇÃO em BARRAS (mantida como estava)
            metricas = calcular_metricas(notas_empilhadas if len(avals_existentes) > 1 else notas_para_metricas)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric('Qtd Alunos (registros de nota)', metricas['Quantidade de Alunos'])
            c2.metric('Média', f"{metricas['Média']:.2f}")
            c3.metric('Mediana', f"{metricas['Mediana']:.2f}")
            c4.metric('Desvio Padrão', f"{metricas['Desvio Padrão']:.2f}")

            if not notas_empilhadas.empty:
                # Criar DataFrame com Nota e Ano
                notas_empilhadas_df = (
                    df_filtrado[['CODPERLET'] + avals_existentes]
                    .melt(id_vars=['CODPERLET'], value_vars=avals_existentes, var_name='Avaliacao', value_name='Nota')
                    .dropna(subset=['Nota'])
                )
                anos_unicos = sorted(notas_empilhadas_df['CODPERLET'].unique())
                st.info(f"Períodos letivos analisados: {', '.join(map(str, anos_unicos))}")

                if len(anos_unicos) > 1:
                    fig_bar = analise_notas_bar(notas_empilhadas_df['Nota'], notas_empilhadas_df['CODPERLET'])
                else:
                    fig_bar = analise_notas_bar(notas_empilhadas_df['Nota'])


                # Se tiver mais de 1 período, mostrar colorido por ano
                if notas_empilhadas_df['CODPERLET'].nunique() > 1:
                    fig_bar = analise_notas_bar(notas_empilhadas_df['Nota'], notas_empilhadas_df['CODPERLET'])
                else:
                    fig_bar = analise_notas_bar(notas_empilhadas_df['Nota'])

                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("Não há notas para o filtro aplicado.")
                
            fig_temporal = grafico_temporal_turma_disciplina(df_filtrado, avals_existentes)
            if fig_temporal:
                st.plotly_chart(fig_temporal, use_container_width=True)

            # ---------- Gráfico por TURMA: DISTRIBUIÇÃO EM BARRAS ----------
            df_plot_turmas = df_filtrado[['CODTURMA', 'CODPERLET'] + avals_existentes].copy()  # inclua CODPERLET
            turmas_para_grafico = turmas_sel if turmas_sel else sorted(df_plot_turmas['CODTURMA'].dropna().unique())

            if not turmas_para_grafico:
                st.info("Não há turmas para gerar os gráficos de distribuição por turma.")
            else:
                st.markdown("**Distribuição (barras) por Turma — cada turma um gráfico**")
                n_cols = 3  # quantos gráficos por linha para as avaliações
                for turma in turmas_para_grafico:
                    df_t = df_plot_turmas[df_plot_turmas['CODTURMA'] == turma].copy()
                    if df_t.empty or df_t[avals_existentes].dropna(how='all').empty:
                        st.write(f"Turma {turma}: sem dados.")
                        continue

                    # Captura os anos distintos da turma para exibir no título do expander
                    anos_turma = sorted(df_t['CODPERLET'].unique())
                    anos_str = ", ".join(map(str, anos_turma))

                    with st.expander(f"Turma {turma} — distribuição por avaliação ({anos_str})"):
                        # Gráficos individuais por avaliação
                        for idx in range(0, len(avals_existentes), n_cols):
                            grupo = avals_existentes[idx: idx + n_cols]
                            row_cols = st.columns(len(grupo))
                            for j, aval in enumerate(grupo):
                                with row_cols[j]:
                                    notas_eval = df_t[aval].dropna()
                                    anos_eval = df_t.loc[notas_eval.index, 'CODPERLET']
                                    if notas_eval.empty:
                                        st.write(f"{aval}: sem dados")
                                        continue
                                    fig_eval = analise_notas_bar(notas_eval, anos=anos_eval)
                                    fig_eval.update_layout(title=f"{aval}")
                                    st.plotly_chart(fig_eval, use_container_width=True)



            # Resumo por período letivo
            resumo = (
                df_filtrado.groupby('CODPERLET')[avals_existentes]
                .agg(['count', 'mean', 'median', 'std'])
            )
            if not resumo.empty:
                mapa_nomes = {
                    'count': 'Qtd. Alunos',
                    'mean': 'Média',
                    'median': 'Mediana',
                    'std': 'Desv. Padrão'
                }
                resumo.columns = [
                    f"{aval} - {mapa_nomes.get(agg, agg)}" 
                    for aval, agg in resumo.columns.to_flat_index()
                ]
                formatador = {
                    col: '{:.0f}' 
                    for col in resumo.columns if 'Qtd. Alunos' in col
                }
                st.dataframe(resumo.style.format(formatador, precision=2, na_rep="N/A"))

    #  # ---------- BOXPLOT POR TURMA ----------
    # st.markdown("### Boxplot por Turma — Distribuição de Notas")

    # if not turmas_para_grafico:
    #     st.info("Não há turmas para gerar o boxplot.")
    # else:
    #     import plotly.express as px

    #     for turma in turmas_para_grafico:
    #         df_t = df_plot_turmas[df_plot_turmas['CODTURMA'] == turma].copy()
    #         if df_t.empty or df_t[avals_existentes].dropna(how='all').empty:
    #             st.write(f"Turma {turma}: sem dados para boxplot.")
    #             continue

    #         # Converter para formato longo (melt)
    #         df_melt = df_t.melt(
    #             id_vars=['CODPERLET'],
    #             value_vars=avals_existentes,
    #             var_name='Avaliação',
    #             value_name='Nota'
    #         ).dropna(subset=['Nota'])

    #         if df_melt.empty:
    #             st.write(f"Turma {turma}: sem dados para boxplot.")
    #             continue

    #         # Criar boxplot com Plotly Express
    #         fig_box = px.box(
    #             df_melt,
    #             x='Avaliação',
    #             y='Nota',
    #             color='CODPERLET',
    #             points='all',  # mostra outliers individuais
    #             title=f"Distribuição de Notas — Turma {turma}"
    #         )

    #         fig_box.update_layout(
    #             xaxis_title="Avaliação",
    #             yaxis_title="Nota",
    #             legend_title="Período Letivo",
    #             boxmode="group"
    #         )

    #         st.plotly_chart(fig_box, use_container_width=True)
            
    # ---------- BOXPLOT GERAL COMPARANDO TURMAS ----------
    st.markdown("### Boxplot Geral — Comparativo entre Turmas")

    if not turmas_para_grafico:
        st.info("Não há turmas para gerar o boxplot geral.")
    else:
        import plotly.express as px

        df_box_all = df_plot_turmas[
            df_plot_turmas['CODTURMA'].isin(turmas_para_grafico)
        ].copy()

        # Converter para formato longo
        df_melt_all = df_box_all.melt(
            id_vars=['CODTURMA', 'CODPERLET'],
            value_vars=avals_existentes,
            var_name='Avaliação',
            value_name='Nota'
        ).dropna(subset=['Nota'])

        if df_melt_all.empty:
            st.info("Sem dados suficientes para gerar o boxplot geral.")
        else:
            fig_box_all = px.box(
                df_melt_all,
                x='CODTURMA',
                y='Nota',
                color='CODPERLET',
                facet_col='Avaliação',   # cria uma coluna para cada avaliação
                facet_col_wrap=3,         # quebra em múltiplas linhas se houver muitas avaliações
                points=False,
                title="Comparativo entre Turmas — Distribuição das Notas"
            )

            fig_box_all.update_layout(
                xaxis_title="Turma",
                yaxis_title="Nota",
                legend_title="Período Letivo",
                boxmode="group"
            )

            st.plotly_chart(fig_box_all, use_container_width=True)

