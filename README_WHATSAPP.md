# WhatsApp + LLM Bot

Módulo opcional do dashboard que conecta um (ou vários) números de WhatsApp
via [Evolution API](https://github.com/EvolutionAPI/evolution-api) e responde
automaticamente quem mandar mensagem usando o **DeepSeek**.

## Arquitetura

```
WhatsApp ─▶ Evolution API (docker) ──webhook──▶  FastAPI (backend/)
                                                      │
                                                      ├─▶ SQLite (instâncias + histórico)
                                                      ├─▶ DeepSeek (gera resposta)
                                                      └─▶ Evolution API (envia resposta)

Painel: Streamlit (pages/1_💬_WhatsApp_Bot.py) ─▶ FastAPI (REST)
```

- **Evolution API**: gateway WhatsApp (Baileys). Roda em Docker.
- **FastAPI** (`backend/`): recebe webhooks, conversa com a LLM e devolve via Evolution.
- **Streamlit**: painel de controle — cria instâncias, mostra QR code, edita prompt, lista conversas.
- **SQLite**: instâncias, prompt do bot e histórico de conversa (arquivo em `data/`).

## Setup rápido

1. **Variáveis de ambiente**

   ```bash
   cp .env.example .env
   # edite .env e preencha DEEPSEEK_API_KEY e (opcionalmente) EVOLUTION_API_KEY
   ```

2. **Suba a Evolution API** (Docker)

   ```bash
   docker compose up -d
   ```

   Confira em <http://localhost:8080> — deve responder algo da Evolution.

3. **Instale dependências Python**

   ```bash
   pip install -r requirements.txt
   ```

4. **Backend FastAPI** (em um terminal)

   ```bash
   uvicorn backend.main:app --reload --port 8000
   ```

5. **Streamlit** (em outro terminal)

   ```bash
   streamlit run app.py
   ```

   Acesse <http://localhost:8501> e clique em **💬 WhatsApp Bot** no menu lateral.

## Como conectar um número

1. Aba **➕ Nova instância** → escolha um nome (ex: `cliente-joao`) e o prompt do bot.
2. Aba **📋 Minhas instâncias** → expanda **📱 QR Code** → **Gerar QR**.
3. No celular do cliente: **WhatsApp → Aparelhos conectados → Conectar um aparelho** → escaneie.
4. O status muda para `open` quando a conexão é confirmada. Pronto — qualquer mensagem recebida será respondida pela LLM.

## Webhook (importante)

A Evolution API roda em Docker e precisa alcançar o backend FastAPI que roda no host:

- **Docker Desktop (Mac/Windows)** e **Linux com `extra_hosts: host-gateway`** (configurado no compose): use `http://host.docker.internal:8000/webhook`.
- **Servidor remoto / produção**: use a URL pública do seu backend (ex: `https://api.seudominio.com/webhook`). Para testar localmente exponha com `ngrok http 8000`.

A URL é definida ao criar cada instância no painel (ou via env `EVOLUTION_WEBHOOK_URL`).

## Sobre o modelo DeepSeek

O nome “DeepSeek V4 Flash” mencionado no pedido **não é um modelo oficial**.
Os modelos publicados pela DeepSeek atualmente são:

- `deepseek-chat` (V3) — uso geral, é o padrão.
- `deepseek-reasoner` (R1) — pensamento estendido.

Mude via `.env`:

```
DEEPSEEK_MODEL=deepseek-chat
```

A integração usa a API OpenAI-compatível da DeepSeek (`https://api.deepseek.com`), então é trivial trocar de modelo no futuro.

## Estrutura de arquivos

```
backend/
  config.py        # leitura de env vars
  db.py            # SQLite (instâncias + mensagens)
  evolution.py     # cliente HTTP Evolution API
  llm.py           # cliente DeepSeek (async)
  main.py          # FastAPI: /instances, /webhook, etc.
pages/
  1_💬_WhatsApp_Bot.py   # painel Streamlit
docker-compose.yml       # Evolution API + Postgres + Redis
.env.example
```

## Pausar / despausar o bot

No painel, cada instância tem um toggle **Ativo**. Mensagens recebidas com o bot pausado são ignoradas (não geram resposta nem entram no histórico).

## Limitações conhecidas

- Mensagens de **grupo** (`@g.us`) e **broadcast** são ignoradas por padrão.
- Suporta apenas mensagens de **texto**. Áudio, imagem, vídeo, doc — ignorados.
- Histórico por contato vai até `HISTORY_LIMIT` mensagens (padrão 20).
- Em produção, considere proteger `/webhook` com um token + validação de origem.
