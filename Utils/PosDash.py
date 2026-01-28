import pandas as pd
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
from datetime import datetime
import streamlit as st
import pandas as pd
import plotly.express as px


def carregar():

    st.title("Taxa Real de Evasão — Pós-Graduação")

    df_pos = st.session_state["dados"].get("cancelamentospos", pd.DataFrame())

    if df_pos.empty:
        st.warning("DataFrame vazio.")
        return

    df = df_pos.copy()
    df.columns = [c.strip() for c in df.columns]
    df['Aluno'] = df['Aluno'].astype(str).str.strip()

    # --------------------------
    # PADRONIZA STATUS
    # --------------------------
    df['NOMESTATUS'] = (
        df['NOMESTATUS']
        .astype(str)
        .str.strip()
        .str.upper()
        .replace({
            'DESISTÊNCIA': 'CANCELADO',
            'DESISTENCIA': 'CANCELADO',
            'DESLIGADO': 'CANCELADO',
            'CANCELAMENTO': 'CANCELADO'
        })
    )

    df['EVADIU'] = (df['NOMESTATUS'] == 'CANCELADO').astype(int)

    
    st.subheader(" Resumo Geral por Período Letivo")

    total_periodo = (
        df.groupby('Período Letivo')['Aluno']
        .nunique()
        .reset_index(name='Total Matriculados')
    )

    cancelados_periodo = (
        df[df['EVADIU'] == 1]
        .groupby('Período Letivo')['Aluno']
        .nunique()
        .reset_index(name='Cancelados')
    )

    resumo_periodo = total_periodo.merge(
        cancelados_periodo,
        on='Período Letivo',
        how='left'
    ).fillna(0)

    resumo_periodo['Taxa de Evasão (%)'] = (
        resumo_periodo['Cancelados'] /
        resumo_periodo['Total Matriculados'] * 100
    ).round(2)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("###  Total x Cancelados")
        st.dataframe(resumo_periodo)

    with col2:
        st.markdown("###  Apenas Cancelados")
        st.dataframe(cancelados_periodo)

    # ==========================================================
    # 📚 ANÁLISE POR CURSO
    # ==========================================================
    total_alunos = (
        df.groupby(['Curso', 'Período Letivo'])['Aluno']
        .nunique()
        .reset_index(name='Total Alunos')
    )

    total_evasao = (
        df[df['EVADIU'] == 1]
        .groupby(['Curso', 'Período Letivo'])['Aluno']
        .nunique()
        .reset_index(name='Alunos Evadidos')
    )

    df_taxa = total_alunos.merge(
        total_evasao,
        on=['Curso', 'Período Letivo'],
        how='left'
    ).fillna(0)

    df_taxa['Taxa de Evasão (%)'] = (
        df_taxa['Alunos Evadidos'] / df_taxa['Total Alunos'] * 100
    ).round(2)

    # ==========================================================
    # 📦 BLOCO RECOLHÍVEL — EVASÃO POR PERÍODO
    # ==========================================================
    with st.expander(" Evasão por Período Letivo", expanded=False):

        st.subheader("Tabela de Evasão por Curso")
        st.dataframe(df_taxa.sort_values('Taxa de Evasão (%)', ascending=False))

        # 🔹 AGRUPA POR PERÍODO (média da taxa ou soma dos evadidos)
        evasao_periodo = (
            df_taxa.groupby('Período Letivo')
            .agg({
                'Alunos Evadidos': 'sum',
                'Total Alunos': 'sum'
            })
            .reset_index()
        )

        evasao_periodo['Taxa de Evasão (%)'] = (
            evasao_periodo['Alunos Evadidos'] /
            evasao_periodo['Total Alunos'] * 100
        ).round(2)

        st.subheader("Taxa de Evasão por Período")

        fig = px.line(
            evasao_periodo,
            x='Período Letivo',
            y='Taxa de Evasão (%)',
            markers=True,
            text='Taxa de Evasão (%)'
        )

        fig.update_traces(textposition="top center")
        st.plotly_chart(fig, use_container_width=True)

    # MATRIZ
    st.subheader(" Matriz de Evasão (%)")
    matriz = df_taxa.pivot(
        index='Curso',
        columns='Período Letivo',
        values='Taxa de Evasão (%)'
    ).fillna(0)

    st.dataframe(matriz)

    # KPI GERAL
    total_geral = df['Aluno'].nunique()
    evadidos_geral = df[df['EVADIU'] == 1]['Aluno'].nunique()
    taxa_geral = round(evadidos_geral / total_geral * 100, 2)

    st.metric("Taxa Geral de Evasão", f"{taxa_geral}%")

    return df_taxa