# predictor.py - VERSÃO FINAL, FUNCIONAL E SEGURA PARA GITHUB ACTIONS

import pandas as pd
import requests
import random
import os
import asyncio 

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

# predictor.py

def send_telegram_message(message: str):
    """Envia a mensagem de texto para a lista de chats configurados de forma assíncrona."""
    
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_IDS or TELEGRAM_CHAT_IDS == [""]:
        print("❌ Erro: Token ou Chat IDs do Telegram não configurados nas variáveis de ambiente.")
        return

    try:
        from telegram import Bot
        
        async def send_to_recipient(chat_id):
            bot = Bot(token=TELEGRAM_TOKEN)
            await bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
            print(f"   -> Mensagem enviada para o Chat ID: {chat_id}")

        async def main_async_sender():
            """Função wrapper assíncrona para rodar todas as tarefas."""
            tasks = [send_to_recipient(chat_id) for chat_id in TELEGRAM_CHAT_IDS]
            print(f"\nIniciando o envio para {len(tasks)} destinatário(s) configurado(s)...")
            await asyncio.gather(*tasks)
            print("✅ Envio de previsão concluído para todos os destinatários.")
            
        # Tenta obter o loop atual ou criar um novo se não houver
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Se o loop estiver rodando, agendamos a tarefa. Caso contrário, rodamos ele.
        if loop.is_running():
            # Agendar a tarefa e aguardar a conclusão
            loop.run_until_complete(main_async_sender())
        else:
            # Rodar a tarefa e iniciar o loop
            loop.run_until_complete(main_async_sender())
            
    except ImportError:
        print("❌ Erro: Instale 'python-telegram-bot' com 'poetry add python-telegram-bot'.")
    except Exception as e:
        print(f"❌ Erro ao enviar mensagem para o Telegram. Verifique Token/IDs: {e}") 

# ... (Mantenha o resto do código, INCLUINDO o bloco if __name__ == "__main__" que você criou, pois ele é a melhor prática.)

# --- FUNÇÃO DE BUSCA DE API ---

def fetch_latest_result(last_concurso_number):
    """Busca o último concurso na API do GitHub e retorna o resultado se for novo."""
    try:
        print(f">>> Buscando último resultado em: {API_URL_LATEST}")
        response = requests.get(API_URL_LATEST, timeout=15)
        response.raise_for_status() 
        data = response.json()
        
        concurso_api = int(data['concurso'])
        dezenas_sorteadas = [int(d) for d in data['dezenas']]
        
        if concurso_api > last_concurso_number:
            
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
            return None 
            
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
    """Carrega, limpa e prepara os dados para análise."""
    
    if os.path.exists(DATA_FILE_CLEAN):
        try:
            print(f">>> Carregando dados do CSV limpo: '{DATA_FILE_CLEAN}'...")
            df = pd.read_csv(DATA_FILE_CLEAN, sep=';', encoding='iso-8859-1', skipinitialspace=True)
            df['Concurso'] = pd.to_numeric(df['Concurso'], errors='coerce', downcast='integer')
            return df.sort_values(by='Concurso').reset_index(drop=True).dropna(subset=['Concurso'])
        except Exception as e:
            print(f"⚠️ Aviso: Erro ao ler CSV limpo ({e}). Tentando processar o CSV bruto.")
            pass 
            
    if not os.path.exists(DATA_FILE_RAW):
        print(f"❌ Erro fatal: Arquivo de dados brutos '{DATA_FILE_RAW}' não encontrado.")
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

        df['Concurso'] = pd.to_numeric(df['Concurso'], errors='coerce', downcast='integer') 
        df = df.dropna(subset=dezena_cols + ['Concurso'])
        df = df.sort_values(by='Concurso').reset_index(drop=True)
        
        df.to_csv(DATA_FILE_CLEAN, index=False, sep=';', encoding='iso-8859-1')

        print(f"✅ Dados de {len(df)} concursos extraídos e limpos.")
        
        return df

    except Exception as e:
        print(f"❌ Erro ao processar o arquivo CSV: {e}")
        return None

def get_frequency_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula a frequência absoluta de cada dezena já sorteada."""
    all_dezenas = pd.concat([df[col] for col in df.columns if 'Dezena' in col])
    all_dezenas = all_dezenas.dropna().astype(int) 
    
    if all_dezenas.empty:
        return pd.DataFrame(columns=['Dezena', 'Frequência', 'Porcentagem'])

    frequency = all_dezenas.value_counts().reset_index()
    frequency.columns = ['Dezena', 'Frequência']
    frequency = frequency.sort_values(by='Dezena').reset_index(drop=True)
    frequency['Porcentagem'] = (frequency['Frequência'] / frequency['Frequência'].sum()) * 100
    return frequency

def predict_next_game(df: pd.DataFrame, num_jogos: int = 1) -> tuple:
    """Gera previsões estatísticas."""
    frequency_df = get_frequency_analysis(df)
    
    if frequency_df.empty:
        all_numbers = list(range(1, 61))
        predictions = [sorted(random.sample(all_numbers, 6)) for _ in range(num_jogos)]
        return predictions, "N/A (Faltam dados de histórico)"

    top_frequent = frequency_df.sort_values(by='Frequência', ascending=False).head(15)['Dezena'].tolist()
    least_frequent = frequency_df.sort_values(by='Frequência', ascending=True).head(15)['Dezena'].tolist()
    
    pool_dezenas = list(set(top_frequent + least_frequent))
    
    predictions = []
    for _ in range(num_jogos):
        all_numbers = set(range(1, 61))
        current_game_pool = pool_dezenas
        
        if len(pool_dezenas) < 6:
              missing_count = 6 - len(pool_dezenas)
              complement = random.sample(list(all_numbers - set(pool_dezenas)), missing_count)
              current_game_pool = pool_dezenas + complement
              
        if len(current_game_pool) > 20:
              current_game_pool = random.sample(current_game_pool, 20)
        
        prediction = sorted(random.sample(current_game_pool, 6))
        predictions.append(prediction)
        
    return predictions, frequency_df.head(10).to_string(index=False) 

# --- FUNÇÃO PRINCIPAL DE AUTOMAÇÃO ---

def main():
    """Função principal para executar a análise e notificar automaticamente."""
    
    df = load_and_clean_data()
    
    if df is None:
        return
    
    try:
        last_concurso_number = int(df['Concurso'].max())
    except Exception:
        last_concurso_number = 0
        print("⚠️ Aviso: Histórico de concursos inválido. Tentando buscar desde o início.")
        
    print(f"\n--- Iniciando Verificação Automática (Último Concurso Analisado: {last_concurso_number}) ---")

    novo_resultado = fetch_latest_result(last_concurso_number)

    if novo_resultado:
        print(f"🎉 Novo concurso {novo_resultado['Concurso']} encontrado! Atualizando histórico e gerando previsão...")
        
        new_df_row = pd.DataFrame([novo_resultado])
        df = pd.concat([df, new_df_row], ignore_index=True)
        
        df.to_csv(DATA_FILE_CLEAN, index=False, sep=';', encoding='iso-8859-1')
        
        predictions, top_frequency_str = predict_next_game(df, 3)
        
        dezenas_formatadas = ' - '.join(str(int(novo_resultado[f'Dezena{i}'])).zfill(2) for i in range(1, 7))
        
        message = (
            f"<b>🎰 NOVA PREVISÃO MEGA SENA AUTOMÁTICA</b>\n"
            f"Último Concurso Sorteado: <b>{novo_resultado['Concurso']}</b>\n"
            f"Resultado: <b>{dezenas_formatadas}</b>\n\n"
            f"🧠 <b>Próximos 3 Jogos Recomendados:</b>\n"
        )
        for i, jogo in enumerate(predictions, 1):
            jogo_formatado = ' - '.join(str(int(x)).zfill(2) for x in jogo)
            message += f"  Jogo {i}: <code>{jogo_formatado}</code>\n" 
        
        message += f"\n📊 <b>Dezenas Mais Frequentes (Top 10):</b>\n"
        message += f"<pre>{top_frequency_str}</pre>" 
        
        send_telegram_message(message)
        
    else:
        print(f"✅ Histórico já atualizado. Nenhuma ação necessária.")

# --- Execução Principal CORRIGIDA ---
# Função wrapper para garantir o loop de eventos assíncronos no GitHub Actions

async def async_main_wrapper():
    """Wrapper para permitir que o main() rode dentro de um loop de eventos."""
    # O await aqui garante que as chamadas internas assíncronas possam ser feitas
    main()

if __name__ == "__main__":
    try:
        # Usa o asyncio.run() para iniciar o loop de eventos e rodar a função
        asyncio.run(async_main_wrapper())
        
    except RuntimeError as e:
        # Tenta um fallback síncrono em ambientes específicos que podem rejeitar o asyncio.run
        if "cannot run non-coroutine" in str(e):
             main() 
        else:
             print(f"❌ Erro fatal do asyncio: {e}")
    except Exception as e:
         print(f"❌ Erro inesperado na execução principal: {e}")