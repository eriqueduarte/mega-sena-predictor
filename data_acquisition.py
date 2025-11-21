# data_acquisition.py - VERSÃO CORRIGIDA

import requests
import pandas as pd
import io
import os
from bs4 import BeautifulSoup

# URL de uma página de terceiros que mantém os dados atualizados em formato de tabela
# (Usaremos uma fonte estável para a extração da tabela)
# Alternativa: 'https://www.sorteonline.com.br/mega-sena/resultados'
WEB_SCRAPING_URL = "https://asloterias.com.br/resultados-da-mega-sena-todos-os-sorteios"
DATA_FILE = "megasena_resultados.csv"

def get_latest_results():
    """
    Busca os resultados da Mega Sena fazendo Web Scraping de uma tabela HTML
    e salva os dados em um CSV limpo.
    """
    print(">>> Tentando Web Scraping para adquirir os resultados...")
    
    try:
        # Pandas pode ler tabelas diretamente de uma URL se a estrutura for simples
        # O argumento header=0 define a primeira linha como cabeçalho
        tabelas = pd.read_html(WEB_SCRAPING_URL, decimal=',', thousands='.', header=0)
        
        # Na maioria dos sites, a tabela principal de resultados é a primeira (índice 0)
        if not tabelas:
            print("❌ Nenhuma tabela encontrada na URL.")
            return None
            
        df = tabelas[0]
        
        # --- Limpeza e Seleção de Colunas (Se necessário) ---
        
        # Vamos garantir que as colunas de dezenas (D1, D2, ..., D6) estejam presentes
        colunas_dezenas = [col for col in df.columns if col.startswith('Dezena')]
        
        if len(colunas_dezenas) < 6:
             print(f"❌ A tabela encontrada não contém as 6 colunas de dezenas esperadas. Colunas encontradas: {df.columns.tolist()}")
             return None

        # Renomeia colunas para simplificar (Ex: Concurso, Data, Dezena1, Dezena2,...)
        df.columns = [
            'Concurso', 'Data', 'Dezena1', 'Dezena2', 'Dezena3', 'Dezena4', 'Dezena5', 'Dezena6', 
            'Ganhadores_Sena', 'Ganhadores_Quina', 'Ganhadores_Quadra', 
            'Valor_Sena', 'Valor_Quina', 'Valor_Quadra', 'Acumulado', 'Estimativa_Prox_Premio'
        ] + df.columns[16:].tolist()

        # Seleciona apenas as colunas relevantes para a análise estatística
        df = df[['Concurso', 'Data', 'Dezena1', 'Dezena2', 'Dezena3', 'Dezena4', 'Dezena5', 'Dezena6']]
        
        # Remove linhas com valores vazios (NaN) nas dezenas
        df = df.dropna(subset=['Dezena1', 'Dezena2', 'Dezena3', 'Dezena4', 'Dezena5', 'Dezena6'])
        
        # Converte o ID do Concurso para número inteiro (importante para ordenação)
        df['Concurso'] = pd.to_numeric(df['Concurso'], errors='coerce', downcast='integer')
        
        # Remove linhas onde o Concurso não pôde ser convertido (ruído)
        df = df.dropna(subset=['Concurso'])
        
        # Salva o DataFrame limpo em um arquivo local
        df.to_csv(DATA_FILE, index=False, encoding='utf-8')
        
        print(f"✅ Dados de {len(df)} concursos extraídos, limpos e salvos em '{DATA_FILE}'.")
        print("💡 Próximo passo: Análise Estatística.")
        return df

    except ValueError as e:
        print(f"❌ Erro de Pandas/BeautifulSoup ao ler a tabela: {e}. Verifique se a URL contém tabelas HTML válidas.")
        return None
    except Exception as e:
        print(f"❌ Ocorreu um erro inesperado: {e}")
        return None

if __name__ == "__main__":
    get_latest_results()