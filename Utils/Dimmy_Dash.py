import pandas as pd
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px

@st.cache_data
def carregar_dados():
    return st.session_state['dados']['dashnotas']

def plot_pizza(data_dict):
    fig, ax = plt.subplots(figsize=(1.5, 1.5))
    
    
    labels = list(data_dict.keys())
    sizes = list(data_dict.values())


    colors = ['#5C2D91', "#C20E0E"] 

    wedges, _ = ax.pie(
        sizes,
        labels=None,  
        startangle=90,
        counterclock=False,
        colors=colors[:len(sizes)] 
    )

    ax.axis('equal')  

    ax.legend(
        wedges,
        labels,
        title="Categorias",
        loc="center left",
        bbox_to_anchor=(1, 0, 0.5, 1),
        fontsize=8,
        title_fontsize=9
    )

    return fig

def analise_notas(notas):
    contagem = notas.value_counts().sort_index()
    df_plot = pd.DataFrame({'Nota': contagem.index, 'Quantidade': contagem.values})
    fig = px.bar(df_plot, x='Nota', y='Quantidade', color_discrete_sequence=['#5C2D91'])
    fig.update_layout(title='Distribuição de Notas')
    return fig


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
        st.error('Nenhum dado disponível para os filtros aplicados..')
        st.stop()

    st.title('Painel de Análise de Notas')
    st.caption('Visualize a distribuição das notas por curso, disciplina e avaliação.')

    # renomeações já existentes
    df.rename(columns={
        'E01': 'Média P1',
        'E02': 'Média P2',
        'MF': 'Média Final',
        'RECF': 'REC Final'
    }, inplace=True)

    # período
    df['CODPERLET'] = df['CODPERLET'].astype(str)
    periodos = sorted(df['CODPERLET'].dropna().unique())
    periodo_sel = st.multiselect('Selecione o Período Letivo', periodos)
    if not periodo_sel:
        st.warning('Selecione pelo menos um período letivo.')
        st.stop()
    df = df[df['CODPERLET'].isin(periodo_sel)]

    # cursos e tabs
    cursos = sorted(df['CURSO'].dropna().unique())
    subtabs = st.tabs(cursos + ['Total'])

    # --- abas por curso ---
    for i, curso in enumerate(cursos):
        with subtabs[i]:
            st.markdown(f'### {curso}')
            df_curso = df[df['CURSO'] == curso].drop_duplicates(subset=['ALUNO', 'NOMEDISC'])

            
            disciplinas = sorted(df_curso['NOMEDISC'].dropna().unique())
            disciplina_sel = st.selectbox('Selecione a disciplina', disciplinas, key=f'disc_{curso}_{i}')

            
            df_filtrado = df_curso[df_curso['NOMEDISC'] == disciplina_sel]

            # 3) agora sim monta as turmas a partir desse df_filtrado (dependente da disciplina)
            
            turmas_na_disc = sorted(df_filtrado['CODTURMA'].dropna().unique())
            if turmas_na_disc:
                turmas_sel = st.multiselect(
                    'Selecione a(s) Turma(s) que ministraram a disciplina',
                    turmas_na_disc,
                    key=f'turmas_{curso}_{i}'
                )
            else:
                st.info('Nenhuma turma encontrada para a disciplina selecionada.')
                turmas_sel = []  # evita erro adiante
                
            if not turmas_sel:
                st.info("Nenhuma turma selecionada — a análise será realizada com **todas as turmas** da disciplina.")
            else:
                st.success(f"Analisando {len(turmas_sel)} turma(s): {', '.join(map(str, turmas_sel))}")


            # 4) usa o filtro por turma(s) caso o usuário selecione alguma
            if turmas_sel:
                df_filtrado = df_filtrado[df_filtrado['CODTURMA'].isin(turmas_sel)]


            # Grupo e avaliações (mantive selectbox aqui, como você tinha originalmente)
            grupo = st.selectbox('Selecione o grupo de avaliação', ['P1', 'P2', 'P3', 'Final'], key=f'grupo_{curso}_{i}')
            avals = get_avaliacoes_por_grupo(grupo)
            avaliacao_sel = st.selectbox('Selecione a avaliação', avals, key=f'aval_{curso}_{i}')

            # Filtra por disciplina e turma(s)
            df_filtrado = df_curso[df_curso['NOMEDISC'] == disciplina_sel]
            if turmas_sel:
                df_filtrado = df_filtrado[df_filtrado['CODTURMA'].isin(turmas_sel)]

            # Protege se coluna não existir
            if avaliacao_sel not in df_filtrado.columns:
                notas = pd.Series([], dtype=float)
            else:
                notas = df_filtrado[avaliacao_sel].dropna()

            # Top 5 por turma (expander)
            with st.expander('Top 5 Alunos por Turma'):
                turmas_na_disc = sorted(df_filtrado['CODTURMA'].dropna().unique())
                if turmas_na_disc:
                    turma_sel = st.selectbox('Selecione a Turma (para Top5)', turmas_na_disc, key=f'top5turma_{curso}_{i}')
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
                if avaliacao_sel in df_filtrado.columns and not df_filtrado[avaliacao_sel].dropna().empty:
                    top3 = (
                        df_filtrado[['RA', 'ALUNO', avaliacao_sel]]
                        .dropna()
                        .sort_values(by=avaliacao_sel, ascending=False)
                        .head(3)
                    )
                    st.dataframe(top3.style.format({avaliacao_sel: '{:.2f}'}))
                else:
                    st.info(f"Coluna '{avaliacao_sel}' não disponível ou sem notas.")

            # Métricas e gráfico de barras
            metricas = calcular_metricas(notas)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric('Qtd Alunos', metricas['Quantidade de Alunos'])
            c2.metric('Média', f"{metricas['Média']:.2f}")
            c3.metric('Mediana', f"{metricas['Mediana']:.2f}")
            c4.metric('Desvio Padrão', f"{metricas['Desvio Padrão']:.2f}")

            if not notas.empty:
                st.plotly_chart(analise_notas(notas))
            else:
                st.info("Não há notas para o filtro aplicado.")

            # Situação (aprovado/reprovado) — critério dinâmico usando 'REC' no nome da avaliação
            if not notas.empty:
                limite_aprovacao = 6 if 'REC' in avaliacao_sel.upper() else 7
                aprovados = (notas >= limite_aprovacao).sum()
                reprovados = (notas < limite_aprovacao).sum()
                total = aprovados + reprovados

                with st.expander("Situação dos Alunos na Avaliação"):
                    if total > 0:
                        porcentagens = {
                            f'Aprovado (≥ {limite_aprovacao})': aprovados,
                            f'Reprovado (< {limite_aprovacao})': reprovados
                        }
                        col1, col2, col3 = st.columns([1, 2, 1])
                        with col2:
                            st.pyplot(plot_pizza(porcentagens))
                    else:
                        st.info("Não há notas suficientes para gerar o gráfico de aprovação.")

            # Resumo por período letivo (se houver dados)
            if avaliacao_sel in df_filtrado.columns:
                resumo = (
                    df_filtrado.groupby('CODPERLET')[avaliacao_sel]
                    .agg(['count', 'mean', 'median', 'std'])
                    .rename(columns={'count': 'Qtd Alunos', 'mean': 'Média', 'median': 'Mediana', 'std': 'Desvio Padrão'})
                    .dropna()
                )
                if not resumo.empty:
                    st.dataframe(resumo.style.format({'Média': '{:.2f}', 'Mediana': '{:.2f}', 'Desvio Padrão': '{:.2f}'}))

    # --- Aba TOTAL ---
    # --- Aba TOTAL ---
    with subtabs[-1]:
        st.markdown('### Total (Todos os Cursos)')

        # Select para escolher um curso específico ou todos
        curso_total_sel = st.selectbox(
            'Selecione o Curso (ou "Todos os Cursos") para análise',
            ['Todos os Cursos'] + cursos,
            index=0,
            key='total_curso'
        )

        # Base de dados a usar (filtrada por curso, se escolher um)
        if curso_total_sel == 'Todos os Cursos':
            df_base = df.copy()
        else:
            df_base = df[df['CURSO'] == curso_total_sel].copy()

        # Multiselect para grupos (chave única)
        grupos_sel = st.multiselect(
            'Selecione um ou mais grupos de avaliação',
            ['P1', 'P2', 'P3', 'Final'],
            key='total_grupos'
        )

        # Junta avaliações dos grupos escolhidos (sem duplicatas)
        avals_tot = []
        for g in grupos_sel:
            avals_tot.extend(get_avaliacoes_por_grupo(g))
        avals_tot = sorted(list(dict.fromkeys(avals_tot)))  # remove duplicatas mantendo ordem

        # Multiselect para avaliações (nenhuma pré-seleção)
        avaliacoes_sel = st.multiselect(
            'Selecione uma ou mais avaliações',
            avals_tot,
            default=[],
            key='total_avals'
        )


        if not avaliacoes_sel:
            st.warning('Selecione ao menos uma avaliação para visualizar os dados.')
        else:
            # garante que usamos apenas avaliações existentes na base filtrada
            avals_existentes = [a for a in avaliacoes_sel if a in df_base.columns]
            if not avals_existentes:
                st.info("As avaliações selecionadas não estão presentes na base/curso escolhido.")
            else:
                # Notas empilhadas para cálculo estatístico
                notas_tot = df_base[avals_existentes].stack().dropna()

                # Quantidade de alunos únicos que tem pelo menos uma nota válida nas avaliações selecionadas
                mask_alunos_com_nota = df_base[avals_existentes].notna().any(axis=1)
                alunos_unicos_com_nota = df_base.loc[mask_alunos_com_nota, 'RA'].nunique()

                metricas_tot = calcular_metricas(notas_tot)
                d1, d2, d3, d4 = st.columns(4)
                d1.metric('Qtd Alunos (únicos com nota)', alunos_unicos_com_nota)
                d2.metric('Média', f"{metricas_tot['Média']:.2f}")
                d3.metric('Mediana', f"{metricas_tot['Mediana']:.2f}")
                d4.metric('Desvio Padrão', f"{metricas_tot['Desvio Padrão']:.2f}")

                # --- Caso: TODOS OS CURSOS -> gráfico de pizza com quantidade por curso ---
                if curso_total_sel == 'Todos os Cursos':
                    # Seleciona linhas onde exista pelo menos uma nota nas avaliações escolhidas
                    mask = df_base[avals_existentes].notna().any(axis=1)
                    df_counts = (
                        df_base[mask]
                        .groupby('CURSO')['RA']
                        .nunique()                # conta alunos únicos por curso
                        .reset_index(name='Quantidade')
                        .sort_values('Quantidade', ascending=False)
                    )

                    if df_counts.empty:
                        st.info("Não há registros de notas nas avaliações selecionadas para gerar o gráfico por curso.")
                    else:
                        # --- Gráfico por curso (Plotly) e situação geral (por aluno) lado a lado ---
                        col_left, col_right = st.columns([1, 1])

                        # Left: pizza por curso
                        with col_left:
                            # Paleta personalizada para cursos
                            custom_colors = {
                                'Direito': '#800020',               # vinho
                                'Engenharia de Software': "#4E9FD0",   # azul claro
                                'Administração de Empresas': '#00008B' # azul escuro
                            }

                            fig_pie = px.pie(
                                df_counts,
                                names='CURSO',
                                values='Quantidade',
                                title='Alunos por Curso (com nota nas avaliações selecionadas)',
                                color='CURSO',
                                color_discrete_map=custom_colors
                            )
                            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                            fig_pie.update_layout(margin=dict(t=40, b=10, l=10, r=10), legend_title_text='Curso')
                            st.plotly_chart(fig_pie, use_container_width=True)

                        # Right: situação geral por aluno (aprovado/reprovado)
                        with col_right:
                            df_ra = df_base[['RA'] + avals_existentes].copy()
                            df_ra_group = df_ra.groupby('RA')[avals_existentes].max()

                            # Remove alunos sem nenhuma nota válida
                            df_ra_group = df_ra_group.dropna(how='all')

                            # Define limite de aprovação baseado em existência de "REC" em alguma avaliação selecionada
                            limite_aprovacao = 6 if any('REC' in aval.upper() for aval in avals_existentes) else 7

                            def aluno_aprovado(row):
                                for col in avals_existentes:
                                    val = row.get(col)
                                    if pd.notna(val) and val >= limite_aprovacao:
                                        return True
                                return False

                            aprovado_mask = df_ra_group.apply(aluno_aprovado, axis=1)
                            aprovados = int(aprovado_mask.sum())
                            total_alunos = int(len(df_ra_group))
                            reprovados = total_alunos - aprovados

                            st.markdown("**Situação geral dos alunos (Todos os Cursos)**")
                            st.write(f"- Total de alunos considerados: **{total_alunos}**")
                            st.write(f"- Aprovados: **{aprovados}**")
                            st.write(f"- Reprovados: **{reprovados}**")

                            if total_alunos > 0:
                                porcentagens = {'Aprovado': aprovados, 'Reprovado': reprovados}
                                st.pyplot(plot_pizza(porcentagens))
                            else:
                                st.info("Não há alunos para calcular situação.")

                # --- Caso: curso específico -> mantém lógica por ALUNO (RA) evitando duplicação ---
                else:
                    df_ra = df_base[['RA'] + avals_existentes].copy()
                    df_ra_group = df_ra.groupby('RA')[avals_existentes].max()

                    # Remove alunos sem nenhuma nota válida
                    df_ra_group = df_ra_group.dropna(how='all')

                    # Define limite de aprovação baseado em existência de "REC" em alguma avaliação selecionada
                    limite_aprovacao = 6 if any('REC' in aval.upper() for aval in avals_existentes) else 7

                    def aluno_aprovado(row):
                        for col in avals_existentes:
                            val = row.get(col)
                            if pd.notna(val) and val >= limite_aprovacao:
                                return True
                        return False

                    aprovado_mask = df_ra_group.apply(aluno_aprovado, axis=1)
                    aprovados = int(aprovado_mask.sum())
                    total_alunos = int(len(df_ra_group))
                    reprovados = total_alunos - aprovados

                    if total_alunos > 0:
                        porcentagens = {
                            'Aprovado': int(aprovados),
                            'Reprovado': int(reprovados)
                        }
                        with st.expander("Situação dos Alunos"):
                            col1, col2, col3 = st.columns([1, 2, 1])
                            with col2:
                                st.pyplot(plot_pizza(porcentagens))
                    else:
                        st.info("Não há notas para calcular aprovação.")
