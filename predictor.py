# predictor.py - VERSÃO FINAL, FUNCIONAL E SEGURA

import pandas as pd
import requests
import random
import os
import asyncio # Adicionado para corrigir o RuntimeWarning e envio múltiplo

# --- CONFIGURAÇÕES DE ARQUIVOS E API ---
DATA_FILE_RAW = "mega.csv" 
DATA_FILE_CLEAN = "megasena_historico_limpo.csv"

# API pública gratuita de resultados de Loterias CAIXA
API_URL_LATEST = "https://loteriascaixa-api.herokuapp.com/api/megasena/latest"

# 🚨 CONFIGURAÇÃO DO TELEGRAM (LENDO DE VARIÁVEIS DE AMBIENTE/SECRETS) 🚨
# O GitHub Actions injeta os valores nas variáveis de ambiente!
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "TOKEN_DE_SEGURANCA_AQUI")

# Recebe os IDs como uma única string separada por vírgulas e a converte em lista de IDs
chat_ids_str = os.environ.get("TELEGRAM_CHAT_IDS", "")
TELEGRAM_CHAT_IDS = [id.strip() for id in chat_ids_str.split(',') if id.strip()]

# --- FUNÇÕES DE UTILIDADE E NOTIFICAÇÃO ---

def send_telegram_message(message: str):
    """Envia a mensagem de texto para a lista de chats configurados de forma assíncrona."""
    
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_IDS:
        print("❌ Erro: Token ou Chat IDs do Telegram não configurados nas variáveis de ambiente.")
        return

    try:
        from telegram import Bot
        
        # Função assíncrona que envia a mensagem para um ID específico
        async def send_to_recipient(chat_id):
            bot = Bot(token=TELEGRAM_TOKEN)
            await bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
            print(f"   -> Mensagem enviada para o Chat ID: {chat_id}")

        # Cria uma lista de tarefas assíncronas (uma para cada destinatário)
        tasks = [send_to_recipient(chat_id) for chat_id in TELEGRAM_CHAT_IDS]
        
        print(f"\nIniciando o envio para {len(tasks)} destinatário(s) configurado(s)...")
        
        # Executa todas as tarefas de envio simultaneamente
        asyncio.run(asyncio.gather(*tasks))
        
        print("✅ Envio de previsão concluído para todos os destinatários.")
        
    except ImportError:
        print("❌ Erro: Instale 'python-telegram-bot' com 'poetry add python-telegram-bot'.")
    except Exception as e:
        print(f"❌ Erro ao enviar mensagem para o Telegram. Verifique Token/IDs: {e}")


# --- RESTANTE DO CÓDIGO (INALTERADO) ---

def fetch_latest_result(last_concurso_number):
# ... [Restante da função fetch_latest_result] ...
# Mantenha o corpo da função inalterado
# ...
    try:
        print(f">>> Buscando último resultado em: {API_URL_LATEST}")
        response = requests.get(API_URL_LATEST, timeout=15)
        response.raise_for_status() # Lança erro para 4xx/5xx
        data = response.json()
        
        # O JSON desta API tem o formato { "concurso": 2700, "dezenas": ["10", "20", ...] }
        concurso_api = int(data['concurso'])
        dezenas_sorteadas = [int(d) for d in data['dezenas']]
        
        if concurso_api > last_concurso_number:
            
            # Dezenas vêm como strings, precisamos ordenar e garantir 6
            if len(dezenas_sorteadas) != 6:
                print(f"⚠️ Aviso: API retornou {len(dezenas_sorteadas)} dezenas para o concurso {concurso_api}. Pulando.")
                return None
            
            dezenas_sorteadas.sort() 
            
            novo_resultado = {
                'Concurso': concurso_api, 
                'Dezena1': dezenas_sorteadas[0], 
                'Dezena2': dezenas_sorteadas[1], 
                'Dezena3': dezenas_sorteadas[2], 
                'Dezena4': dezenas_sorteadas[3], 
                'Dezena5': dezenas_sorteadas[4], 
                'Dezena6': dezenas_sorteadas[5]
            }
            return novo_resultado
        else:
            return None # Nenhum concurso novo
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro de conexão ao buscar API ({type(e).__name__}): {e}")
        return None
    except (KeyError, ValueError) as e:
        print(f"❌ Erro: Formato da API inesperado ou dado inválido. Chave/Valor: {e}")
        return None
    except Exception as e:
        print(f"❌ Erro inesperado no processamento da API: {e}")
        return None

# --- FUNÇÕES DE ANÁLISE DE DADOS (Inalteradas) ---

def load_and_clean_data():
# ... [Restante da função load_and_clean_data] ...
# Mantenha o corpo da função inalterado
# ...
    # Tenta ler o CSV limpo (preferencialmente)
    if os.path.exists(DATA_FILE_CLEAN):
        try:
            print(f">>> Carregando dados do CSV limpo: '{DATA_FILE_CLEAN}'...")
            df = pd.read_csv(DATA_FILE_CLEAN, sep=';', encoding='iso-8859-1', skipinitialspace=True)
            # Garante que a coluna 'Concurso' é numérica para o .max()
            df['Concurso'] = pd.to_numeric(df['Concurso'], errors='coerce', downcast='integer')
            return df.sort_values(by='Concurso').reset_index(drop=True).dropna(subset=['Concurso'])
        except Exception as e:
            print(f"⚠️ Aviso: Erro ao ler CSV limpo ({e}). Tentando processar o CSV bruto.")
            # O código continua abaixo para processar o bruto se o limpo falhar
            pass 
            
    # Processamento do Arquivo Bruto (Se limpo não existir ou falhar)
    if not os.path.exists(DATA_FILE_RAW):
        print(f"❌ Erro fatal: Arquivo de dados brutos '{DATA_FILE_RAW}' não encontrado.")
        print("O sistema não pode funcionar sem dados iniciais.")
        return None
        
    print(f">>> Processando dados brutos de '{DATA_FILE_RAW}'...")
    
    try:
        temp_names = [f'col_{i}' for i in range(15)] 
        
        df = pd.read_csv(
            DATA_FILE_RAW, 
            sep=',',              
            encoding='iso-8859-1', 
            skipinitialspace=True, 
            header=None,           
            skiprows=2,            
            engine='python',       
            names=temp_names,      
            on_bad_lines='warn'   
        )
        
        cols_to_select_names = ['col_0', 'col_2', 'col_3', 'col_4', 'col_5', 'col_6', 'col_7']
        df = df[cols_to_select_names].copy()
        df.columns = ['Concurso', 'Dezena1', 'Dezena2', 'Dezena3', 'Dezena4', 'Dezena5', 'Dezena6']
        
        dezena_cols = [col for col in df.columns if 'Dezena' in col]
        for col in dezena_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce', downcast='integer')

        df['Concurso'] = pd.to_numeric(df['Concurso'], errors='coerce', downcast='integer') # Garante que Concurso é int
        df = df.dropna(subset=dezena_cols + ['Concurso'])
        df = df.sort_values(by='Concurso').reset_index(drop=True)
        
        df.to_csv(DATA_FILE_CLEAN, index=False, sep=';', encoding='iso-8859-1')

        print(f"✅ Dados de {len(df)} concursos extraídos e limpos.")
        
        return df

    except Exception as e:
        print(f"❌ Erro ao processar o arquivo CSV: {e}")
        return None

def get_frequency_analysis(df: pd.DataFrame) -> pd.DataFrame:
# ... [Restante da função get_frequency_analysis] ...
# Mantenha o corpo da função inalterado
# ...
    all_dezenas = pd.concat([df[col] for col in df.columns if 'Dezena' in col])
    all_dezenas = all_dezenas.dropna().astype(int) # Limpeza de segurança
    
    if all_dezenas.empty:
        # Retorna um DataFrame vazio se não houver dados válidos (para evitar o erro 'nan')
        return pd.DataFrame(columns=['Dezena', 'Frequência', 'Porcentagem'])

    frequency = all_dezenas.value_counts().reset_index()
    frequency.columns = ['Dezena', 'Frequência']
    frequency = frequency.sort_values(by='Dezena').reset_index(drop=True)
    frequency['Porcentagem'] = (frequency['Frequência'] / frequency['Frequência'].sum()) * 100
    return frequency

def predict_next_game(df: pd.DataFrame, num_jogos: int = 1) -> tuple:
# ... [Restante da função predict_next_game] ...
# Mantenha o corpo da função inalterado
# ...
    frequency_df = get_frequency_analysis(df)
    
    if frequency_df.empty:
        # Fallback se não houver histórico válido
        all_numbers = list(range(1, 61))
        predictions = [sorted(random.sample(all_numbers, 6)) for _ in range(num_jogos)]
        return predictions, "N/A (Faltam dados de histórico)"

    top_frequent = frequency_df.sort_values(by='Frequência', ascending=False).head(15)['Dezena'].tolist()
    least_frequent = frequency_df.sort_values(by='Frequência', ascending=True).head(15)['Dezena'].tolist()
    
    pool_dezenas = list(set(top_frequent + least_frequent))
    
    predictions = []
    for _ in range(num_jogos):
        # Garante que sempre haja 60 números disponíveis
        all_numbers = set(range(1, 61))
        
        current_game_pool = pool_dezenas
        
        # Se o pool for menor que 6, complementa com números aleatórios não usados
        if len(pool_dezenas) < 6:
              missing_count = 6 - len(pool_dezenas)
              complement = random.sample(list(all_numbers - set(pool_dezenas)), missing_count)
              current_game_pool = pool_dezenas + complement
              
        # Se o pool for muito grande, limitamos a 20 números para amostra (pode ser ajustado)
        if len(current_game_pool) > 20:
              current_game_pool = random.sample(current_game_pool, 20)
        
        prediction = sorted(random.sample(current_game_pool, 6))
        predictions.append(prediction)
        
    return predictions, frequency_df.head(10).to_string(index=False) 

# --- FUNÇÃO PRINCIPAL DE AUTOMAÇÃO (Inalterada) ---

def main():
# ... [Restante da função main] ...
# Mantenha o corpo da função inalterado
# ...
    # 1. Carrega ou cria dados históricos
    df = load_and_clean_data()
    
    if df is None:
        return
    
    # Tenta obter o último concurso válido do histórico
    try:
        last_concurso_number = int(df['Concurso'].max())
    except Exception:
        # Se o histórico for inválido (nan, etc.), começa a busca do 0 (primeira execução)
        last_concurso_number = 0
        print("⚠️ Aviso: Histórico de concursos inválido. Tentando buscar desde o início.")
        
    print(f"\n--- Iniciando Verificação Automática (Último Concurso Analisado: {last_concurso_number}) ---")

    # 2. Busca o último concurso na API
    novo_resultado = fetch_latest_result(last_concurso_number)

    if novo_resultado:
        print(f"🎉 Novo concurso {novo_resultado['Concurso']} encontrado! Atualizando histórico e gerando previsão...")
        
        # 3. Adiciona o novo resultado ao DataFrame
        new_df_row = pd.DataFrame([novo_resultado])
        df = pd.concat([df, new_df_row], ignore_index=True)
        
        # Salva a atualização
        df.to_csv(DATA_FILE_CLEAN, index=False, sep=';', encoding='iso-8859-1')
        
        # 4. Gera a nova previsão baseada no histórico atualizado
        predictions, top_frequency_str = predict_next_game(df, 3)
        
        # 5. Formata a mensagem para o Telegram (usando HTML para negrito e código)
        dezenas_formatadas = ' - '.join(str(int(novo_resultado[f'Dezena{i}'])).zfill(2) for i in range(1, 7))
        
        message = (
            f"<b>🎰 NOVA PREVISÃO MEGA SENA AUTOMÁTICA</b>\n"
            f"Último Concurso Sorteado: <b>{novo_resultado['Concurso']}</b>\n"
            f"Resultado: <b>{dezenas_formatadas}</b>\n\n"
            f"🧠 <b>Próximos 3 Jogos Recomendados:</b>\n"
        )
        for i, jogo in enumerate(predictions, 1):
            # Formata o número com zero à esquerda (ex: 01, 10, 20)
            jogo_formatado = ' - '.join(str(int(x)).zfill(2) for x in jogo)
            message += f"  Jogo {i}: <code>{jogo_formatado}</code>\n" 
        
        message += f"\n📊 <b>Dezenas Mais Frequentes (Top 10):</b>\n"
        message += f"<pre>{top_frequency_str}</pre>" # Tag <pre> mantém a formatação do DataFrame
        
        # 6. Envia a notificação
        send_telegram_message(message)
        
    else:
        print(f"✅ Histórico já atualizado. Nenhuma ação necessária.")

# --- Execução Principal ---
if __name__ == "__main__":
    main()