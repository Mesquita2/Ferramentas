from io import BytesIO
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


    alunos_estado["size"] = np.log1p(alunos_estado["Qtd Alunos"]) * 15


    fig = px.scatter_mapbox(
    alunos_estado,
    lat="lat",
    lon="lon",
    size="size",
    color="Qtd Alunos",
    hover_name="ESTADO",
    hover_data={"Qtd Alunos": True, "% Alunos": True, "lat": False, "lon": False},
    zoom=3,
    height=600,
    )


    fig.update_layout(
    mapbox_style="carto-darkmatter", # pode trocar por "open-street-map"
    margin={"r":0,"t":0,"l":0,"b":0},
    )


    st.plotly_chart(fig, use_container_width=True)
    
def analise(_df_dummy=None):
    import pandas as pd
    from io import BytesIO
    import plotly.express as px

    # 🔎 Procura o arquivo manual no session_state
    manual_df = st.session_state["dados"].get("AlunosPósporregião", pd.DataFrame())

    df = manual_df.copy()
    df = df.dropna(how="all")  # remove linhas totalmente vazias

    # ----------------------------------------------------
    # ACHA AUTOMATICAMENTE ONDE COMEÇA A TABELA
    # ----------------------------------------------------
    start_idx = None
    for i, val in enumerate(df.iloc[:, 0].astype(str)):
        if "LESTE" in val.upper() or "SUL" in val.upper() or "NORTE" in val.upper():
            start_idx = i
            break

    if start_idx is None:
        st.error("Não foi possível identificar a tabela no arquivo.")
        return

    df = df.iloc[start_idx:]  # corta só a parte útil

    # Mantém só as 3 primeiras colunas úteis
    df = df.iloc[:, :3]
    df.columns = ["ZONA", "TOTAL", "PERCENTUAL"]

    # ----------------------------------------------------
    # LIMPEZA
    # ----------------------------------------------------
    df["ZONA"] = df["ZONA"].astype(str).str.upper().str.strip()
    df["TOTAL"] = pd.to_numeric(df["TOTAL"], errors="coerce")

    df["PERCENTUAL"] = (
        df["PERCENTUAL"]
        .astype(str)
        .str.replace("%", "")
        .str.replace(",", ".")
    )
    df["% Alunos"] = pd.to_numeric(df["PERCENTUAL"], errors="coerce").round(2)

    df = df.dropna(subset=["TOTAL"])
    df = df[~df["ZONA"].isin(["NAN", "ZONA", "REGIÃO", "REGIAO", "0", ""])]

    tabela = df[["ZONA", "TOTAL", "% Alunos"]].rename(columns={"TOTAL": "Qtd Alunos"})

    # ----------------------------------------------------
    # VISUAL
    # ----------------------------------------------------
    st.subheader("Distribuição de Alunos por Zona — (Arquivo Manual)")
    st.dataframe(tabela.sort_values("% Alunos", ascending=False))

    fig = px.bar(
        tabela,
        x="ZONA",
        y="% Alunos",
        text="% Alunos",
        color="ZONA"
    )
    st.plotly_chart(fig, use_container_width=True)

import time
import requests
import pandas as pd
import streamlit as st

@st.cache_data(show_spinner=False)
def enriquecer_ceps(ceps_unicos):

    resultados = []
    total = len(ceps_unicos)

    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, cep in enumerate(ceps_unicos):

        status_text.text(f"Consultando CEP {i+1} de {total}...")

        try:
            r = requests.get(f"https://viacep.com.br/ws/{cep}/json/", timeout=3)
            data = r.json()

            if "erro" not in data:
                resultados.append({
                    "CEP": cep,
                    "BAIRRO_API": data.get("bairro"),
                    "CIDADE_API": data.get("localidade"),
                    "UF_API": data.get("uf")
                })
        except:
            pass

        progress_bar.progress((i+1) / total)

    status_text.text("Consulta finalizada ✅")

    return pd.DataFrame(resultados)


def gerar_excel_multiplas(dfs):
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for nome, df in dfs.items():
                df.to_excel(writer, index=False, sheet_name=nome)
            output.seek(0)
    return output

import re

def normalizar_bairro(bairro):
    if pd.isna(bairro):
        return ""

    bairro = bairro.upper()

    # remove acentos
    bairro = (
        bairro.replace("Á","A").replace("Ã","A").replace("Â","A")
              .replace("É","E").replace("Ê","E")
              .replace("Í","I")
              .replace("Ó","O").replace("Õ","O")
              .replace("Ú","U")
              .replace("Ç","C")
    )

    # remove palavras inúteis
    lixo = ["BAIRRO","CONJUNTO","CJ","LOT","LOTEAMENTO","RESIDENCIAL","VILA"]
    for palavra in lixo:
        bairro = bairro.replace(palavra, "")

    # remove números romanos e extras
    bairro = re.sub(r"\bI{1,3}\b", "", bairro)
    bairro = re.sub(r"\d+", "", bairro)

    return bairro.strip()

def analise_zonas(df):
    import pandas as pd
    import plotly.express as px
    import streamlit as st

    st.subheader("Classificação Inteligente por Zonas Urbanas")

    df = df.copy()

    # --------------------------------------------------
    # GARANTE COLUNAS
    # --------------------------------------------------
    if 'BAIRRO_LIMPO' not in df.columns:
        st.error("Coluna BAIRRO_LIMPO não encontrada.")
        return

    # --------------------------------------------------
    # DICIONÁRIO BASE DE ZONAS (TERESINA)
    # --------------------------------------------------
    mapa_zonas_base = {

        # NORTE
        "MOCAMBINHO": "NORTE",
        "SANTA MARIA": "NORTE",
        "AEROPORTO": "NORTE",
        "PRIMAVERA": "NORTE",
        "AGUA MINERAL": "NORTE",
        "SAO JOAQUIM": "NORTE",
        "MORROS": "NORTE",

        # LESTE
        "ININGA": "LESTE",
        "FATIMA": "LESTE",
        "JOQUEI": "LESTE",
        "HORTO": "LESTE",
        "SAO CRISTOVAO": "LESTE",
        "URUGUAI": "LESTE",
        "NOIVOS": "LESTE",
        "VALE QUEM TEM": "LESTE",
        "MORADA DO SOL": "LESTE",
        "RECANTO DAS PALMEIRAS": "LESTE",

        # SUL
        "PROMORAR": "SUL",
        "ANGELIM": "SUL",
        "PARQUE PIAUI": "SUL",
        "PARQUE IDEAL": "SUL",
        "TABULETA": "SUL",
        "SACI": "SUL",
        "BELA VISTA": "SUL",
        "LOURIVAL PARENTE": "SUL",

        # CENTRO
        "CENTRO": "CENTRO",
        "CABRAL": "CENTRO",
        "MARQUES": "CENTRO",
        "PICARRA": "CENTRO",
        "VERMELHA": "CENTRO",
        "PORTO DO CENTRO": "CENTRO",

        # SUDESTE
        "ITARARE": "SUDESTE",
        "DIRCEU": "SUDESTE",
        "RENASCENCA": "SUDESTE",
        "TANCREDO NEVES": "SUDESTE",
        "CIDADE JARDIM": "SUDESTE",
        "PARQUE SUL": "SUDESTE",
    }

    # --------------------------------------------------
    # CLASSIFICADOR INTELIGENTE
    # --------------------------------------------------
    def classificar_zona(bairro):
        if pd.isna(bairro):
            return "OUTROS"

        bairro = str(bairro).upper()

        for chave in mapa_zonas_base:
            if chave in bairro:
                return mapa_zonas_base[chave]

        return "OUTROS"

    df['ZONA'] = df['BAIRRO_LIMPO'].apply(classificar_zona)

    # --------------------------------------------------
    # ANÁLISE
    # --------------------------------------------------
    zona_resumo = (
        df.groupby('ZONA')['RA']
        .nunique()
        .reset_index(name='Qtd Alunos')
    )

    total = zona_resumo['Qtd Alunos'].sum()
    zona_resumo['% Alunos'] = (zona_resumo['Qtd Alunos'] / total * 100).round(2)

    st.dataframe(zona_resumo.sort_values('% Alunos', ascending=False))

    fig = px.bar(
        zona_resumo,
        x='ZONA',
        y='% Alunos',
        text='% Alunos',
        color='ZONA'
    )

    st.plotly_chart(fig, use_container_width=True)

    # --------------------------------------------------
    # INTELIGÊNCIA DO SISTEMA (EVOLUIR MODELO)
    # --------------------------------------------------
    st.subheader("Bairros não classificados (OUTROS)")
    outros = (
        df[df['ZONA'] == "OUTROS"]['BAIRRO_LIMPO']
        .value_counts()
        .reset_index()
    )
    outros.columns = ['Bairro', 'Qtd']

    st.dataframe(outros.head(20))

    return zona_resumo

def carregar():

    tab1, tab2, tab3 = st.tabs([
        " Evasão",
        " Mapa de Alunos",
        " Api_Normalizacao",
    ])

    # ---------- ABA 1: Evasão ----------
    with tab1:
        st.title("Taxa Real de Evasão — Pós-Graduação")

        df_pos = st.session_state["dados"].get("cancelamentospos", pd.DataFrame())

        if df_pos.empty:
            st.warning("DataFrame vazio.")
        else:
            df = df_pos.copy()
            df.columns = [c.strip() for c in df.columns]
            df['Aluno'] = df['Aluno'].astype(str).str.strip()

            # -------------------------------------------------
            # PADRONIZA STATUS
            # -------------------------------------------------
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

            # -------------------------------------------------
            # RESUMO GERAL POR PERÍODO
            # -------------------------------------------------
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
                st.markdown("### Total x Cancelados")
                st.dataframe(resumo_periodo)

            with col2:
                st.markdown("### Apenas Cancelados")
                st.dataframe(cancelados_periodo)

            # -------------------------------------------------
            # ANÁLISE POR CURSO
            # -------------------------------------------------
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

            # -------------------------------------------------
            # EXPANDER POR PERÍODO
            # -------------------------------------------------
            with st.expander("Evasão por Período Letivo", expanded=False):

                periodos = sorted(df_taxa['Período Letivo'].dropna().unique())
                periodo_sel = st.selectbox("Escolha um Período", ["Todos"] + periodos)

                # -------------------- TODOS OS PERÍODOS --------------------
                if periodo_sel == "Todos":

                    resumo_periodo_por_ano = (
                        df_taxa.groupby('Período Letivo')
                        .agg({'Alunos Evadidos': 'sum', 'Total Alunos': 'sum'})
                        .reset_index()
                    )

                    resumo_periodo_por_ano['Taxa de Evasão (%)'] = (
                        resumo_periodo_por_ano['Alunos Evadidos'] /
                        resumo_periodo_por_ano['Total Alunos'] * 100
                    ).round(2)

                    st.dataframe(resumo_periodo_por_ano)

                    fig_trend = px.line(
                        resumo_periodo_por_ano,
                        x='Período Letivo',
                        y='Taxa de Evasão (%)',
                        markers=True
                    )
                    st.plotly_chart(fig_trend, use_container_width=True)

                    for periodo in periodos:
                        with st.expander(f"Detalhes — {periodo}"):
                            df_periodo = df_taxa[df_taxa['Período Letivo'] == periodo]

                            colA, colB = st.columns([2,3])

                            with colA:
                                st.dataframe(df_periodo.sort_values('Taxa de Evasão (%)', ascending=False))

                            with colB:
                                fig = px.bar(
                                    df_periodo.sort_values('Taxa de Evasão (%)', ascending=True),
                                    x='Taxa de Evasão (%)',
                                    y='Curso',
                                    orientation='h',
                                    text='Taxa de Evasão (%)'
                                )
                                st.plotly_chart(fig, use_container_width=True)

                # -------------------- UM PERÍODO --------------------
                else:
                    df_periodo = df_taxa[df_taxa['Período Letivo'] == periodo_sel]

                    colA, colB = st.columns([2,3])

                    with colA:
                        st.dataframe(df_periodo.sort_values('Taxa de Evasão (%)', ascending=False))

                    with colB:
                        fig = px.bar(
                            df_periodo.sort_values('Taxa de Evasão (%)', ascending=True),
                            x='Taxa de Evasão (%)',
                            y='Curso',
                            orientation='h',
                            text='Taxa de Evasão (%)'
                        )
                        st.plotly_chart(fig, use_container_width=True)

            # -------------------------------------------------
            # MATRIZ DE EVASÃO
            # -------------------------------------------------
            st.subheader("Matriz de Evasão (%)")

            matriz = df_taxa.pivot(
                index='Curso',
                columns='Período Letivo',
                values='Taxa de Evasão (%)'
            ).fillna(0)

            st.dataframe(matriz)

            # -------------------------------------------------
            # KPI GERAL
            # -------------------------------------------------
            total_geral = df['Aluno'].nunique()
            evadidos_geral = df[df['EVADIU'] == 1]['Aluno'].nunique()
            taxa_geral = round(evadidos_geral / total_geral * 100, 2)

            st.metric("Taxa Geral de Evasão", f"{taxa_geral}%")

            # -------------------------------------------------
            # DOWNLOAD EXCEL
            # -------------------------------------------------
            dfs_tab1 = {
                "resumo_periodo": resumo_periodo,
                "cancelados_periodo": cancelados_periodo,
                "evasao_por_curso": df_taxa,
                "matriz_evasao": matriz.reset_index()
            }

            excel_tab1 = gerar_excel_multiplas(dfs_tab1)

            st.download_button(
                label="Baixar relatório de Evasão (Excel)",
                data=excel_tab1,
                file_name="relatorio_evasao.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    # ---------- ABA 2: Mapa e análise ----------
    with tab2:
        df_mapa = st.session_state["dados"].get("alunospos.XLSX", pd.DataFrame()).copy()
        # df_geo = st.session_state["dados"].get("relatorio_geografia_pos", pd.DataFrame()).copy()
        if df_mapa.empty:
            st.warning("DataFrame de alunos vazio.")
        else:
            # chama a sua função de mapa (que você já tem)
            mapa_alunos(df_mapa)
            # chama a análise por zona/cidade (que você já tem)
            analise(df_mapa)
            
            # df_geo['BAIRRO_LIMPO'] = df_geo['BAIRRO_API'].apply(normalizar_bairro)
            # analise_zonas(df_geo)

            # --- Calcular as tabelas que apareceram na aba Mapa ---
            # por cidade
            alunos_local = (
                df_mapa.assign(CIDADE=df_mapa['CIDADE'].astype(str).str.upper())
                .groupby(['CIDADE', 'ESTADO'])['RA']
                .nunique()
                .reset_index(name='Qtd Alunos')
            )
            total = alunos_local['Qtd Alunos'].sum()
            alunos_local['% Alunos'] = (alunos_local['Qtd Alunos'] / total * 100).round(2)

            # por estado
            alunos_estado = (
                df_mapa.groupby('ESTADO')['RA']
                .nunique()
                .reset_index(name='Qtd Alunos')
            )
            total_estado = alunos_estado['Qtd Alunos'].sum()
            alunos_estado['% Alunos'] = (alunos_estado['Qtd Alunos'] / total_estado * 100).round(2)

            dfs_tab2 = {
                "alunos_por_cidade": alunos_local.reset_index(drop=True),
                "alunos_por_estado": alunos_estado.reset_index(drop=True),
                "alunos_raw": df_mapa.reset_index(drop=True)
            }
            excel_tab2 = gerar_excel_multiplas(dfs_tab2)
            st.download_button(
                label="Baixar relatório de Localização (Excel)",
                data=excel_tab2,
                file_name="relatorio_localizacao.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    # ---------- ABA 3: API / Normalização e Download ----------
    with tab3:
        st.write("API para padronizar CEP e geração de relatório")

        # df_raw = st.session_state["dados"].get("alunospos.XLSX", pd.DataFrame()).copy()
        # if df_raw.empty:
        #     st.warning("DataFrame de alunos vazio.")
        # else:
        #     # Limpeza CEP
        #     df_raw['CEP'] = df_raw['CEP'].astype(str).str.extract(r'(\d{8})', expand=False)

        #     ceps_unicos = df_raw['CEP'].dropna().unique().tolist()
        #     st.write(f"CEPs únicos a enriquecer: {len(ceps_unicos)}")

        #     # Enriquecer (função com cache)
        #     df_ceps = enriquecer_ceps(ceps_unicos)

        #     # Merge - resultados do enriquecimento
        #     df_merged = df_raw.merge(df_ceps, on="CEP", how="left")

        #     # Criar colunas limpas de cidade/uf/bairro preferindo API
        #     df_merged['BAIRRO_LIMPO'] = df_merged['BAIRRO_API'].fillna(df_merged.get('BAIRRO', ''))
        #     df_merged['CIDADE_LIMPA'] = df_merged['CIDADE_API'].fillna(df_merged.get('CIDADE', ''))
        #     df_merged['UF_LIMPA'] = df_merged['UF_API'].fillna(df_merged.get('ESTADO', ''))

        #     # Tabelas resumidas para exportar
        #     alunos_cidade = (
        #         df_merged.groupby(['CIDADE_LIMPA', 'UF_LIMPA'])['RA']
        #         .nunique()
        #         .reset_index(name='Qtd Alunos')
        #     )
        #     total_cidade = alunos_cidade['Qtd Alunos'].sum()
        #     alunos_cidade['% Alunos'] = (alunos_cidade['Qtd Alunos'] / total_cidade * 100).round(2)

        #     alunos_estado = (
        #         df_merged.groupby(['UF_LIMPA'])['RA']
        #         .nunique()
        #         .reset_index(name='Qtd Alunos')
        #     )
        #     total_estado = alunos_estado['Qtd Alunos'].sum()
        #     alunos_estado['% Alunos'] = (alunos_estado['Qtd Alunos'] / total_estado * 100).round(2)

        #     # zonas de Teresina
        #     df_teresina = df_merged[
        #         (df_merged['CIDADE_LIMPA'].astype(str).str.upper() == "TERESINA") &
        #         (df_merged['UF_LIMPA'].astype(str).str.upper() == "PI")
        #     ].copy()

        #     mapa_zonas_teresina = {
        #         "MOCAMBINHO": "NORTE", "SANTA MARIA": "NORTE", "AEROPORTO": "NORTE",
        #         "PRIMAVERA": "NORTE", "ÁGUA MINERAL": "NORTE",
        #         "FÁTIMA": "LESTE", "JOQUEI": "LESTE", "SÃO CRISTÓVÃO": "LESTE",
        #         "HORTO": "LESTE", "ININGA": "LESTE",
        #         "PARQUE PIAUÍ": "SUL", "PROMORAR": "SUL", "REDENÇÃO": "SUL",
        #         "ANGELIM": "SUL", "BELA VISTA": "SUL",
        #         "CENTRO": "CENTRO", "CABRAL": "CENTRO", "MARQUÊS": "CENTRO"
        #     }

        #     df_teresina['BAIRRO_LIMPO'] = df_teresina['BAIRRO_LIMPO'].astype(str).str.upper().str.strip()
        #     df_teresina['ZONA'] = df_teresina['BAIRRO_LIMPO'].map(mapa_zonas_teresina).fillna("OUTROS")

        #     alunos_zona = (
        #         df_teresina.groupby('ZONA')['RA']
        #         .nunique()
        #         .reset_index(name="Qtd Alunos")
        #     )
        #     total_zona = alunos_zona['Qtd Alunos'].sum()
        #     alunos_zona['% Alunos'] = (alunos_zona['Qtd Alunos'] / total_zona * 100).round(2)

        #     # Monta dicionário para múltiplas abas no Excel
        #     dfs_para_exportar = {
        #         "ceps_enriquecidos": df_merged.reset_index(drop=True),
        #         "alunos_por_cidade": alunos_cidade.reset_index(drop=True),
        #         "alunos_por_estado": alunos_estado.reset_index(drop=True),
        #         "zonas_teresina": alunos_zona.reset_index(drop=True)
        #     }

        #     excel_bytes = gerar_excel_multiplas(dfs_para_exportar)

        #     st.markdown("### Preview - amostra de CEPs enriquecidos")
        #     st.dataframe(df_merged.head(50))

        #     st.download_button(
        #         label=" Baixar relatório completo (Excel)",
        #         data=excel_bytes,
        #         file_name="relatorio_geografia_alunos.xlsx",
        #         mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        #     )

    # retornar df_taxa para compatibilidade (opcional)
    # try:
    #     return df_taxa
    # except NameError:
    #     return None