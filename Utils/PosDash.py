import pandas as pd
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
from datetime import datetime
import streamlit as st
import pandas as pd
import plotly.express as px
import pydeck as pdk

import numpy as np
import pydeck as pdk

def mapa_alunos(df):

    st.title("Distribuição Geográfica dos Alunos")

    df = df.copy()
    df.columns = df.columns.str.strip().str.upper()

    if not {'CEP','CIDADE','ESTADO','RA'}.issubset(df.columns):
        st.error("Colunas necessárias não encontradas.")
        st.write(df.columns.tolist())
        return

    # --------------------------
    # LIMPA CEP
    # --------------------------
    df['CEP'] = df['CEP'].astype(str).str.extract(r'(\d{8})', expand=False)
    df = df[df['CEP'].notna()]

    if df.empty:
        st.warning("Nenhum CEP válido encontrado.")
        return

    # --------------------------
    # PADRONIZA CIDADE
    # --------------------------
    df['CIDADE'] = df['CIDADE'].astype(str).str.strip().str.upper()

    mapa_cidades = {
        "TERESIA": "TERESINA",
        "TER": "TERESINA",
        "TERE": "TERESINA",
        "TERESINA ": "TERESINA",
        "TERESINA-PI": "TERESINA"
    }

    df['CIDADE'] = df['CIDADE'].replace(mapa_cidades)

    # --------------------------
    # TABELA POR CIDADE (SUA LÓGICA)
    # --------------------------
    alunos_local = (
        df.groupby(['CIDADE','ESTADO'])['RA']
        .nunique()
        .reset_index(name="Qtd Alunos")
    )
    total = alunos_local['Qtd Alunos'].sum()
    alunos_local['% Alunos'] = (alunos_local['Qtd Alunos'] / total * 100).round(2)

    st.subheader("Tabela por Cidade")
    st.dataframe(alunos_local.sort_values('% Alunos', ascending=False))

    # --------------------------
    # AGREGAÇÃO PARA O MAPA (POR ESTADO)
    # --------------------------
    alunos_estado = (
        df.groupby('ESTADO')['RA']
        .nunique()
        .reset_index(name='Qtd Alunos')
    )

    total_estado = alunos_estado['Qtd Alunos'].sum()
    alunos_estado['% Alunos'] = (alunos_estado['Qtd Alunos'] / total_estado * 100).round(2)
    st.subheader("Tabela por Estado")
    st.dataframe(alunos_estado.sort_values('% Alunos', ascending=False))

    # --------------------------
    # COORDENADAS DOS ESTADOS
    # --------------------------
    coords_estados = {
        "AC": (-9.974, -67.824), "AL": (-9.665, -35.735), "AP": (0.034, -51.069),
        "AM": (-3.119, -60.021), "BA": (-12.971, -38.501), "CE": (-3.717, -38.543),
        "DF": (-15.793, -47.882), "ES": (-20.315, -40.312), "GO": (-16.686, -49.264),
        "MA": (-2.530, -44.302), "MT": (-15.601, -56.097), "MS": (-20.469, -54.620),
        "MG": (-19.916, -43.934), "PA": (-1.455, -48.490), "PB": (-7.115, -34.864),
        "PR": (-25.428, -49.273), "PE": (-8.047, -34.877), "PI": (-5.091, -42.803),
        "RJ": (-22.906, -43.172), "RN": (-5.794, -35.211), "RS": (-30.034, -51.217),
        "RO": (-8.761, -63.903), "RR": (2.823, -60.675), "SC": (-27.595, -48.548),
        "SP": (-23.550, -46.633), "SE": (-10.947, -37.073), "TO": (-10.184, -48.333)
    }

    alunos_estado["lat"] = alunos_estado["ESTADO"].map(lambda x: coords_estados.get(x, (None, None))[0])
    alunos_estado["lon"] = alunos_estado["ESTADO"].map(lambda x: coords_estados.get(x, (None, None))[1])
    alunos_estado = alunos_estado.dropna(subset=["lat","lon"])

    # TAMANHO INTELIGENTE (não explode)
    alunos_estado["radius"] = np.log1p(alunos_estado["Qtd Alunos"]) * 15000

    # --------------------------
    # MAPA PYDECK PROFISSIONAL
    # --------------------------
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=alunos_estado,
        get_position='[lon, lat]',
        get_radius='radius',
        get_fill_color='[220, 30, 0, 180]',
        pickable=True,
    )

    view_state = pdk.ViewState(latitude=-14, longitude=-52, zoom=4)

    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip={
            "html": "<b>Estado:</b> {ESTADO} <br/> <b>Alunos:</b> {Qtd Alunos} <br/> <b>%:</b> {% Alunos}",
            "style": {"backgroundColor": "black", "color": "white"}
        }
    )

    st.subheader("Mapa de Concentração por Estado")
    st.pydeck_chart(deck)

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
    #  ANÁLISE POR CURSO
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
    # BLOCO RECOLHÍVEL — EVASÃO POR PERÍODO
    # ==========================================================
    with st.expander(" Evasão por Período Letivo", expanded=False):

        st.subheader("Tabela de Evasão por Curso")
        st.dataframe(df_taxa.sort_values('Taxa de Evasão (%)', ascending=False))

        # AGRUPA POR PERÍODO (média da taxa ou soma dos evadidos)
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

    df_mapa = st.session_state["dados"].get("alunospos.XLSX", pd.DataFrame())
    mapa_alunos(df_mapa)

    
    return df_taxa
        
