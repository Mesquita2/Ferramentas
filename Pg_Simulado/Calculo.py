# 

def carregar():
    import io
    import streamlit as st
    import pandas as pd
    import numpy as np

    st.title("Cálculo de Notas do Simulado")

    @st.cache_data
    def carregar_dados(arquivo):
        try:
            return pd.read_excel(arquivo)
        except Exception as e:
            st.error(f"Erro ao carregar o arquivo: {e}")
            return pd.DataFrame()

    def ajustes_dataframe(df):
        df['Student ID'] = df['Student ID'].astype(str).str.zfill(7).copy()
        df['ALUNO'] = df['Student First Name'].fillna('') + ' ' + df['Student Last Name'].fillna('')
        df['ALUNO'] = df['ALUNO'].str.strip()

        df = df[(df['Student ID'] != '0') & (df['ALUNO'] != '')].copy()
        df.rename(columns={'Student ID': 'RA', 'ALUNO': 'NOMEALUNO'}, inplace=True)
        return df

    def calcular_notas(df, questoes_anuladas):
        df = df.copy()
        ids = df['RA'].astype(str).str.zfill(7)

        # Pontos originais
        df['Earned Points Original'] = df['Earned Points'].fillna(0)

        # Ajustar pontos possíveis
        df['Possible Points Ajustado'] = df['Possible Points'].replace(0, np.nan)

        # Calcular bônus por questões anuladas
        bonus_total = pd.Series(0, index=ids.unique())
        for q in questoes_anuladas:
            coluna = f"#{q} Points Earned"
            if coluna in df.columns:
                ganhos = (df[coluna].fillna(0) == 0).astype(int)
                bonus = pd.Series(ganhos.values, index=ids).groupby(level=0).sum()
                bonus_total = bonus_total.add(bonus, fill_value=0)

        df['Bonus Anuladas'] = ids.map(bonus_total).fillna(0)

        # Calcular nota final
        df['Earned Points Final'] = df['Earned Points Original'] + df['Bonus Anuladas']
        df['NOTAS'] = np.minimum((df['Earned Points Final'] * 1.25) / df['Possible Points Ajustado'], 1).fillna(0) * 10

        return df[['RA', 'NOMEALUNO', 'Possible Points', 'Earned Points Original', 'Bonus Anuladas', 'Earned Points Final', 'NOTAS']]

    # Interface
    uploaded_file = st.file_uploader("Envie o arquivo de notas (Excel)", type=["xlsx"])

    if uploaded_file:
        df_original = carregar_dados(uploaded_file)
        st.subheader("Dados Originais")
        st.dataframe(df_original)

        df_ajustado = ajustes_dataframe(df_original)

        questoes_anuladas_input = st.text_input("Informe questões anuladas (separadas por vírgula):", value="")
        questoes_anuladas = [int(q.strip()) for q in questoes_anuladas_input.split(",") if q.strip().isdigit()]

        if st.button("Calcular Notas"):
            df_final = calcular_notas(df_ajustado, questoes_anuladas)

            df_final['NOTAS'] = pd.to_numeric(df_final['NOTAS'], errors='coerce').round(2)
            df_final['NOTAS'] = df_final['NOTAS'].apply(lambda x: f"{x:.2f}".replace('.', ','))

            st.subheader("Notas Finais")
            st.dataframe(df_final)

            output = io.BytesIO()
            df_final.to_csv(output, index=False, sep=';', encoding='utf-8', header=True)
            output.seek(0)

            st.download_button(
                label="⬇ Baixar Notas Tratadas (CSV)",
                data=output,
                file_name="notas_tratadas.csv",
                mime="text/csv"
            )
