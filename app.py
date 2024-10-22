import streamlit as st
import pandas as pd
import plotly.express as px
import re
from io import BytesIO
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import os

# Authentication setup for Streamlit Cloud
config = {
    'credentials': {
        'usernames': {
            os.getenv('STREAMLIT_USER'): {
                'name': os.getenv('STREAMLIT_NAME'),
                'password': os.getenv('STREAMLIT_PASSWORD')
            }
        }
    },
    'cookie': {
        'name': 'streamlit_auth',
        'key': os.getenv('STREAMLIT_COOKIE_KEY'),
        'expiry_days': 30
    }
}

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

name, authentication_status, username = authenticator.login('Login', 'main')

if authentication_status:
    # Load the cleaned dataset
    def load_data():
        # Load the full dataset to clean the date formats
        df = pd.read_excel('portfolio_combined.xlsx')
        
        # Split multiple sectors separated by commas into separate rows
        df = df.assign(Industria=df['Industria'].str.split(',')).explode('Industria')
        df['Industria'] = df['Industria'].str.strip()
        
        # Define an extended function to extract dates from the various possible formats in 'Column6'
        def extract_dates_extended(row):
            acquired_date = None
            exited_date = None
            
            # Extract 'Acquired Date' in various formats
            acquired_match = re.findall(r'Acquired Date[:\-]?\s?(\w+\s\d{4}|\d{4}|\w+-\d{2,4}|\w+ de \d{4}|\w+\sde\s\d{4})', row)
            if acquired_match:
                acquired_date = acquired_match[-1]  # Use the latest acquired date found
            
            # Extract 'Exited Date' in various formats
            exited_match = re.findall(r'Exited Date[:\-]?\s?(\w+\s\d{4}|\d{4}|\w+-\d{2,4}|\w+ de \d{4}|\w+\sde\s\d{4})', row)
            if exited_match:
                exited_date = exited_match[-1]  # Use the latest exited date found
            
            # Handle other cases like single years, multiple dates in one entry, abbreviated months
            other_dates = re.findall(r'(\d{4}|\w+-\d{2,4}|\w+\s\d{4}|\w+ de \d{4})', row)
            if not acquired_date and other_dates:
                acquired_date = other_dates[0]  # Assume the first date is the acquired date if no label is given
            if not exited_date and len(other_dates) > 1:
                exited_date = other_dates[1]  # Assume the second date is the exited date if available
            
            return pd.Series([acquired_date, exited_date])

        # Apply the extended function to create new columns
        df[['Acquired Date', 'Exited Date']] = df['Column6'].apply(extract_dates_extended)

        # Convert acquired and exited dates to a standardized format (year only)
        def standardize_year(date_str):
            if pd.isna(date_str):
                return None
            # Standardize formats like 'May-24', 'mayo de 2024', 'May 2024', etc.
            match = re.search(r'(\d{4})', date_str)
            if match:
                return int(match.group(1))
            # Handle formats like 'Apr-19', 'May-21'
            match = re.search(r'(\w+)-(\d{2})', date_str)
            if match:
                year = int('20' + match.group(2)) if int(match.group(2)) <= 24 else int('19' + match.group(2))
                return year
            return None

        df['Acquired Year'] = df['Acquired Date'].apply(standardize_year)
        df['Exited Year'] = df['Exited Date'].apply(standardize_year)

        return df

    # Load data
    df = load_data()

    # Streamlit app title
    st.title('Análise de Portfólio de Investimentos')

    # Explicação inicial sobre o trabalho
    st.markdown("## Contexto do Trabalho")
    st.markdown("Este projeto foi desenvolvido a partir de um trabalho de web scraping e análise de dados com o auxílio de Inteligência Artificial. Foram coletadas informações sobre aquisições e saídas de investimentos de diversos fundos americanos. O objetivo é trazer insights impactantes sobre os setores mais investidos, o desempenho dos fundos ao longo do tempo e as tendências do mercado.")

    # Resumo dos dados
    st.markdown("## Resumo dos Dados")
    st.markdown(f"Foram analisados um total de **{len(df)} registros**, contendo informações de várias empresas e setores.")

    # Sidebar filters
    st.sidebar.header('Filtrar por:')
    selected_sector = st.sidebar.multiselect('Selecione o(s) Setor(es)', df['Industria'].unique(), default=df['Industria'].unique())
    selected_origin = st.sidebar.multiselect('Selecione a Origem do Fundo', df['Site de Origem'].unique(), default=df['Site de Origem'].unique())

    # Filter data based on selections
    filtered_df = df[(df['Industria'].isin(selected_sector)) & (df['Site de Origem'].isin(selected_origin))]

    # Display the filtered data
    st.dataframe(filtered_df)

    # Quantidades por setor
    st.subheader('Quantidades por Setor')
    sector_count = filtered_df['Industria'].value_counts().reset_index()
    sector_count.columns = ['Industria', 'Quantidade']
    st.markdown(f"Neste conjunto de dados, temos informações sobre investimentos em **{len(sector_count)} setores** diferentes. Abaixo, visualizamos a distribuição desses investimentos.")
    fig_sector = px.bar(sector_count, x='Industria', y='Quantidade', title='Investimentos por Setor')
    fig_sector.update_layout(xaxis_title='Setor', yaxis_title='Quantidade de Investimentos')
    st.plotly_chart(fig_sector)

    # Quantidades por fundo
    st.subheader('Quantidades por Fundo')
    fund_count = filtered_df['Site de Origem'].value_counts().reset_index()
    fund_count.columns = ['Site de Origem', 'Quantidade']
    st.markdown(f"Os dados também mostram o desempenho de **{len(fund_count)} fundos** diferentes. Abaixo, visualizamos quantos investimentos cada fundo realizou.")
    fig_fund_count = px.bar(fund_count, x='Site de Origem', y='Quantidade', title='Investimentos por Fundo')
    fig_fund_count.update_layout(xaxis_title='Fundo', yaxis_title='Quantidade de Investimentos')
    st.plotly_chart(fig_fund_count)

    # Acquisitions by Year
    st.subheader('Aquisições ao Longo dos Anos')
    st.markdown("Vamos analisar a linha do tempo dos eventos de aquisições para entender picos de atividade e tendências gerais do mercado.")
    yearly_acquisitions = filtered_df.dropna(subset=['Acquired Year']).groupby(['Acquired Year', 'Site de Origem']).size().reset_index(name='Quantidade de Aquisições')
    fig_acquisitions = px.line(yearly_acquisitions, x='Acquired Year', y='Quantidade de Aquisições', color='Site de Origem', title='Aquisições ao Longo do Tempo')
    fig_acquisitions.update_layout(xaxis_title='Ano', yaxis_title='Quantidade de Aquisições')
    st.plotly_chart(fig_acquisitions)

    # Top 5 Sectors by Acquisitions per Year
    st.subheader('Top 5 Setores por Ano')
    st.markdown("Abaixo visualizamos os cinco principais setores que receberam mais aquisições em cada ano.")
    top_sectors_per_year = filtered_df.dropna(subset=['Acquired Year']).groupby(['Acquired Year', 'Industria']).size().reset_index(name='Quantidade de Aquisições')
    top_sectors_per_year = top_sectors_per_year.sort_values(['Acquired Year', 'Quantidade de Aquisições'], ascending=[True, False]).groupby('Acquired Year').head(5)
    fig_top_sectors_per_year = px.line(top_sectors_per_year, x='Acquired Year', y='Quantidade de Aquisições', color='Industria', title='Top 5 Setores por Ano')
    fig_top_sectors_per_year.update_layout(xaxis_title='Ano', yaxis_title='Quantidade de Aquisições')
    st.plotly_chart(fig_top_sectors_per_year)

    # Acquisitions by Sector in the Last 2 Years
    st.subheader('Aquisições por Setor nos Últimos 2 Anos')
    st.markdown("Abaixo, visualizamos as aquisições realizadas por setor nos últimos dois anos para entender as tendências mais recentes.")
    recent_years = df['Acquired Year'].max() - 1
    recent_acquisitions = filtered_df[filtered_df['Acquired Year'] >= recent_years]
    recent_sector_count = recent_acquisitions.groupby(['Industria']).size().reset_index(name='Quantidade de Aquisições')
    fig_recent_sectors = px.bar(recent_sector_count, x='Industria', y='Quantidade de Aquisições', title='Aquisições por Setor nos Últimos 2 Anos')
    fig_recent_sectors.update_layout(xaxis_title='Setor', yaxis_title='Quantidade de Aquisições')
    st.plotly_chart(fig_recent_sectors)

    # Display Conclusion
    st.markdown("## Conclusões e Insights")
    st.markdown("- **Tendências Setoriais**: Foi possível identificar quais setores receberam mais investimentos ao longo do tempo, destacando aqueles que estão em alta no mercado.")
    st.markdown("- **Aquisições Recentes**: Analisando os últimos dois anos, conseguimos entender quais setores continuam atraindo investimentos significativos.")
    st.markdown("- **Comparação entre Fundos**: Alguns fundos se destacaram pela quantidade de aquisições realizadas, enquanto outros apresentaram um crescimento mais estável ao longo dos anos.")

    # Download filtered data as Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        filtered_df.to_excel(writer, index=False)
        writer.save()
        processed_data = output.getvalue()

    st.sidebar.download_button(
        label="Baixar Dados Filtrados em Excel",
        data=processed_data,
        file_name='dados_filtrados.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

    authenticator.logout('Logout', 'sidebar')

elif authentication_status == False:
    st.error('Username/password is incorrect')

elif authentication_status == None:
    st.warning('Please enter your username and password')
