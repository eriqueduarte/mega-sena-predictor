# predictor.py - VERSÃO UNIFICADA E ESTÁVEL COM VALIDAÇÃO DE PREVISÃO

import pandas as pd
import requests
import random
import os
import asyncio 
import json # NOVO: Para salvar e carregar o estado do preditor
from concurrent.futures import ThreadPoolExecutor

# --- CONFIGURAÇÕES DE ARQUIVOS E API ---
DATA_FILE_RAW = "mega.csv" 
DATA_FILE_CLEAN = "megasena_historico_limpo.csv"
STATE_FILE = "predictor_state.json" # NOVO: Arquivo para salvar o estado (previsão anterior e acertos)

# API pública gratuita de resultados de Loterias CAIXA
API_URL_LATEST = "https://loteriascaixa-api.herokuapp.com/api/megasena/latest"

# 🚨 CONFIGURAÇÃO DO TELEGRAM (LENDO DE VARIÁVEIS DE AMBIENTE/SECRETS) 🚨
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "TOKEN_DE_SEGURANCA_AQUI")
chat_ids_str = os.environ.get("TELEGRAM_CHAT_IDS", "")
TELEGRAM_CHAT_IDS = [id.strip() for id in chat_ids_str.split(',') if id.strip()]


# --- FUNÇÃO DE ENVIO TELEGRAM (ESTÁVEL) ---

async def async_send_telegram_message(message: str):
    """Função assíncrona real que faz o envio da mensagem."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_IDS or TELEGRAM_CHAT_IDS == [""]:
        print("❌ Erro: Token ou Chat IDs do Telegram não configurados nas variáveis de ambiente.")
        return

    try:
        from telegram import Bot
        
        async def send_to_recipient(chat_id):
            bot = Bot(token=TELEGRAM_TOKEN)
            await bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
            print(f"   -> Mensagem enviada para o Chat ID: {chat_id}")

        tasks = [send_to_recipient(chat_id) for chat_id in TELEGRAM_CHAT_IDS]
        
        print(f"\nIniciando o envio para {len(tasks)} destinatário(s) configurado(s)...")
        await asyncio.gather(*tasks) 
        
        print("✅ Envio de previsão concluído para todos os destinatários.")
        
    except ImportError:
        print("❌ Erro: Instale 'python-telegram-bot' com 'poetry add python-telegram-bot'.")
    except Exception as e:
        # Erros da API do Telegram (401, 400) ou de rede cairão aqui
        print(f"❌ Erro ao enviar mensagem para o Telegram. Verifique Token/IDs: {e}") 

def send_telegram_message(message: str):
    """Função síncrona que chama a função assíncrona de forma segura (sem conflito de loop)."""
    try:
        asyncio.run(async_send_telegram_message(message))
    except RuntimeError as e:
        if "already running" in str(e):
            print("⚠️ Aviso: Loop já em execução. Tentando ThreadPoolExecutor...")
            with ThreadPoolExecutor(max_workers=1) as executor:
                loop = asyncio.get_event_loop()
                loop.run_in_executor(executor, lambda: asyncio.run(async_send_telegram_message(message)))
        else:
             print(f"❌ Erro de runtime no envio de Telegram: {e}")
    except Exception as e:
         print(f"❌ Erro inesperado no envio de Telegram: {e}")

# --- FUNÇÕES DE PERSISTÊNCIA DE ESTADO (NOVAS) ---

def load_state():
    """Carrega o estado do preditor (última previsão feita, total de acertos)."""
    default_state = {
        'last_predicted_concurso': 0,
        'last_predictions': [],
        'total_sena_hits': 0,
        'total_quina_hits': 0,
        'total_quadra_hits': 0
    }
    if os.path.exists(STATE_FILE):
        try:
            print(f">>> Carregando estado do preditor de: '{STATE_FILE}'...")
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                # Garante que o estado tenha todas as chaves
                return {**default_state, **state} 
        except Exception as e:
            print(f"⚠️ Aviso: Erro ao carregar estado do preditor ({e}). Iniciando com estado padrão.")
    return default_state

def save_state(state):
    """Salva o estado atual do preditor."""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=4)
        print(f">>> Estado do preditor salvo em: '{STATE_FILE}'")
    except Exception as e:
        print(f"❌ Erro ao salvar estado do preditor: {e}")

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
                'Dezena6': dezenas_sorteadas[5],
                'DezenasSorteadas': dezenas_sorteadas # Adiciona a lista de dezenas para facilitar a validação
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

# --- FUNÇÕES DE ANÁLISE DE DADOS ---
def load_and_clean_data():
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

# --- FUNÇÃO DE VALIDAÇÃO (NOVA) ---

def check_prediction_hit(predicted_games: list[list[int]], drawn_numbers: list[int]) -> tuple[int, int]:
    """Compara as previsões com as dezenas sorteadas. Retorna o maior número de acertos e o índice do jogo."""
    max_hits = 0
    best_game_index = 0
    
    drawn_set = set(drawn_numbers)
    
    for i, game in enumerate(predicted_games, 1):
        game_set = set(game)
        hits = len(game_set.intersection(drawn_set))
        
        if hits > max_hits:
            max_hits = hits
            best_game_index = i
            
    return max_hits, best_game_index

# --- FUNÇÃO PRINCIPAL DE AUTOMAÇÃO (MODIFICADA) ---

def main():
    """Função principal para executar a análise, validar a previsão e notificar automaticamente."""
    
    # 1. Carregar dados de histórico
    df = load_and_clean_data()
    if df is None:
        return
        
    # 2. Carregar estado do preditor
    predictor_state = load_state()
    
    try:
        last_concurso_number = int(df['Concurso'].max())
    except Exception:
        last_concurso_number = 0
        print("⚠️ Aviso: Histórico de concursos inválido. Tentando buscar desde o início.")
        
    print(f"\n--- Iniciando Verificação Automática (Último Concurso Analisado: {last_concurso_number}) ---")

    # 3. Buscar novo resultado
    novo_resultado = fetch_latest_result(last_concurso_number)

    if novo_resultado:
        print(f"🎉 Novo concurso {novo_resultado['Concurso']} encontrado! Atualizando histórico e gerando previsão...")
        
        concurso_sorteado = novo_resultado['Concurso']
        dezenas_sorteadas = novo_resultado['DezenasSorteadas']
        
        # Atualizar histórico (df)
        new_df_row = pd.DataFrame([{k: novo_resultado[k] for k in novo_resultado if k != 'DezenasSorteadas'}])
        df = pd.concat([df, new_df_row], ignore_index=True)
        df.to_csv(DATA_FILE_CLEAN, index=False, sep=';', encoding='iso-8859-1')
        
        # --- NOVO: VALIDAÇÃO DA PREVISÃO ANTERIOR ---
        
        validation_message = ""
        
        if (predictor_state['last_predicted_concurso'] == concurso_sorteado and 
            predictor_state['last_predictions']):
            
            # A previsão a ser checada é a que foi feita para o concurso sorteado atual
            last_predictions = [list(map(int, p)) for p in predictor_state['last_predictions']]
            max_hits, best_game_index = check_prediction_hit(last_predictions, dezenas_sorteadas)
            
            # Atualizar contadores
            if max_hits == 6:
                predictor_state['total_sena_hits'] += 1
                hit_name = "SENA"
            elif max_hits == 5:
                predictor_state['total_quina_hits'] += 1
                hit_name = "QUINA"
            elif max_hits == 4:
                predictor_state['total_quadra_hits'] += 1
                hit_name = "QUADRA"
            else:
                hit_name = f"{max_hits} acertos"

            print(f"✅ Validação: Previsão do Concurso {concurso_sorteado} resultou em {max_hits} acertos.")

            if max_hits >= 4:
                validation_message = (
                    f"\n⭐ <b>VALORIZAÇÃO da Previsão do Concurso {concurso_sorteado}:</b>\n"
                    f"  O Jogo <b>{best_game_index}</b> acertou <b>{max_hits} dezenas</b> ({hit_name})! 🎉"
                )
            else:
                 validation_message = (
                    f"\n😐 <b>VALORIZAÇÃO da Previsão do Concurso {concurso_sorteado}:</b>\n"
                    f"  Maior acerto: <b>{max_hits} dezenas</b>."
                )

        else:
            validation_message = "\n⚠️ Aviso: Não foi possível validar a previsão anterior (dados ausentes/inconsistentes)."

        # --- FIM VALIDAÇÃO ---

        # --- GERAÇÃO E ARMAZENAMENTO DA NOVA PREVISÃO ---
        predictions, top_frequency_str = predict_next_game(df, 3)
        
        # Salvar novo estado para a próxima execução
        predictor_state['last_predicted_concurso'] = concurso_sorteado + 1 # Previsão é para o próximo concurso
        # Salva as previsões como strings para serialização JSON
        predictor_state['last_predictions'] = [list(map(str, p)) for p in predictions] 
        save_state(predictor_state)

        # --- PREPARAR MENSAGEM TELEGRAM ---
        
        dezenas_sorteadas_formatadas = ' - '.join(str(d).zfill(2) for d in dezenas_sorteadas)

        message = (
            f"<b>🎰 NOVA PREVISÃO MEGA SENA AUTOMÁTICA</b>\n"
            f"Último Concurso Sorteado: <b>{concurso_sorteado}</b>\n"
            f"Resultado: <b>{dezenas_sorteadas_formatadas}</b>"
        )
        
        # Adicionar mensagem de validação
        message += validation_message 
        
        # Adicionar total de acertos
        hits_summary = (
            f"\n\n🏆 <b>ESTATÍSTICAS DO PREDITOR (Total Acertos):</b>\n"
            f"  Sena (6 acertos): <b>{predictor_state['total_sena_hits']}</b> vez(es)\n"
            f"  Quina (5 acertos): <b>{predictor_state['total_quina_hits']}</b> vez(es)\n"
            f"  Quadra (4 acertos): <b>{predictor_state['total_quadra_hits']}</b> vez(es)"
        )
        message += hits_summary
        
        # Adicionar nova previsão
        message += f"\n\n🧠 <b>Próximos 3 Jogos Recomendados (Concurso {concurso_sorteado + 1}):</b>\n"
        
        for i, jogo in enumerate(predictions, 1):
            jogo_formatado = ' - '.join(str(int(x)).zfill(2) for x in jogo)
            message += f"  Jogo {i}: <code>{jogo_formatado}</code>\n" 
        
        message += f"\n📊 <b>Dezenas Mais Frequentes (Top 10):</b>\n"
        message += f"<pre>{top_frequency_str}</pre>"
        
        send_telegram_message(message)
        
    else:
        print(f"✅ Histórico já atualizado. Nenhuma ação necessária.")


# --- Execução Principal (PONTO DE ENTRADA) ---

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
         print(f"❌ Erro inesperado na execução principal: {e}")
