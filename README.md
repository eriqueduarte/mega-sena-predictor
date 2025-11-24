🧠 Mega Sena Predictor e Notificador Automático
Este projeto é um sistema de análise estatística e automação desenvolvido em Python para prever possíveis resultados da Mega Sena e enviar as sugestões de jogos diretamente para o Telegram.

🌟 Visão Geral
O sistema funciona em modo automático (com agendamento externo), buscando o resultado do último concurso via API. Se um novo sorteio for encontrado, ele atualiza o histórico, realiza uma análise estatística (baseada em frequência e atraso das dezenas) e gera 3 jogos de previsão, enviando-os como notificação no Telegram.

🛠️ Tecnologias Utilizadas
Linguagem: Python 3.x

Gerenciador de Dependências: Poetry

Análise de Dados: pandas

Coleta de Dados: requests (para comunicação com a API de resultados)

Notificação: python-telegram-bot

Arquivos de Dados: megasena_historico_limpo.csv (base de dados de resultados)

🚀 Configuração e Instalação
Siga os passos abaixo para configurar o ambiente e executar o projeto:

1. Clonando o Repositório
Bash

git clone https://github.com/SeuUsuario/mega-sena-predictor.git # Substitua
cd mega-sena-predictor
2. Configurando o Ambiente (Poetry)
Instale todas as dependências do projeto usando o Poetry:

Bash

poetry install
poetry shell
3. Configuração do Telegram
Para que as notificações funcionem, é necessário configurar seu Bot Token e Chat ID no arquivo predictor.py.

TELEGRAM_TOKEN = "SEU_TOKEN_DO_BOT_AQUI"

TELEGRAM_CHAT_ID = "SEU_CHAT_ID_AQUI"

4. Base de Dados Histórica
O projeto requer um arquivo CSV com o histórico de todos os concursos da Mega Sena.

Arquivo: megasena_historico.csv (ou o nome que você usou no seu load_and_clean_data()).

Ação: Baixe um CSV completo de resultados da Mega Sena e salve-o na pasta raiz do projeto com o nome correto.

📝 Funcionalidades Principais (predictor.py)
O script principal (predictor.py) possui as seguintes etapas:

load_and_clean_data(): Carrega e limpa o arquivo CSV histórico, garantindo que apenas as dezenas e o número do concurso sejam processados.

fetch_latest_result(): Consulta uma API externa (como loteriascaixa-api.herokuapp.com) para verificar o número do último concurso sorteado.

predict_next_game(): Aplica a lógica estatística (combinação de dezenas mais frequentes e dezenas mais atrasadas) para gerar 3 jogos de previsão.

send_telegram_message(): Envia a previsão formatada (incluindo o resultado do concurso recém-verificado e a lista de jogos sugeridos) para o seu chat privado ou grupo no Telegram.

⚙️ Execução e Automação
O projeto foi desenhado para rodar automaticamente e verificar o status da loteria.

Execução Manual (Teste)
Execute o script dentro do ambiente Poetry:

Bash

poetry run python predictor.py
Se houver um novo concurso, a previsão será gerada e enviada. Caso contrário, ele informará que o histórico está atualizado.

Agendamento (Piloto Automático)
Para que o sistema seja realmente um preditor automático, ele deve ser agendado para rodar após os sorteios (geralmente quartas-feiras e sábados, após as 22h).

Windows: Use o Agendador de Tarefas.

Linux/macOS: Use o Crontab.

O comando a ser agendado é:

Bash

# Comando de exemplo (ajuste o caminho se necessário)
poetry run python SEU_CAMINHO/mega-sena-analise/predictor.py
📂 Estrutura do Projeto
mega-sena-predictor/
├── predictor.py              # Script principal (Lógica de API, Análise e Telegram)
├── megasena_historico.csv    # Arquivo com todos os resultados brutos
├── pyproject.toml            # Configuração do Poetry
├── README.md                 # Este arquivo
└── .gitignore                
🤝 Contribuição
Contribuições são bem-vindas para melhorar a precisão dos modelos preditivos (ex: Markov Chains, Machine Learning).

Faça um fork do projeto.

Crie uma branch para sua funcionalidade (git checkout -b feature/melhoria-ml).

Faça o commit das suas alterações.

Abra um Pull Request.
