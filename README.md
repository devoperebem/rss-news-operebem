# 📰 RSS News API

API REST de notícias financeiras com coleta automática, tradução inteligente e armazenamento em SQLite.

**🌐 API em Produção**: [https://news-operebem.up.railway.app](https://news-operebem.up.railway.app)

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![Railway](https://img.shields.io/badge/Deploy-Railway-blueviolet.svg)](https://railway.app/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 🎯 Funcionalidades

- ✅ **11 fontes RSS** (Bloomberg, The Wall Street Journal, CNBC, InfoMoney, etc)
- ✅ **Tradução automática** para português com detecção de idioma
- ✅ **API REST segura** com autenticação via API Key
- ✅ **CORS configurável** - Restringe acesso por domínio
- ✅ **Zero duplicação** (constraint UNIQUE no banco)
- ✅ **Coleta 24/7** a cada 30 segundos
- ✅ **Limpeza automática** de notícias antigas (>24h)
- ✅ **Arquitetura unificada** (coletor + API em 1 container)

---

## 📡 Endpoints da API

### Base URL
```
https://news-operebem.up.railway.app/api
```

### Públicos (sem autenticação)

#### `GET /api/health`
Health check simples.

**Resposta**:
```json
{
  "success": true,
  "status": "online",
  "timestamp": "2025-10-15T13:38:59.894226"
}
```

---

### Protegidos (requer API Key)

**Autenticação**: Header `X-API-Key: sua-chave` ou query `?api_key=sua-chave`

#### `GET /api/noticias`
Lista todas as notícias.

**Parâmetros opcionais**:
- `fonte` - Filtrar por fonte (ex: `Bloomberg`)
- `limit` - Limitar resultados (ex: `10`)

**Exemplo**:
```bash
curl -H "X-API-Key: sua-chave" \
  "https://news-operebem.up.railway.app/api/noticias?limit=5"
```

**Resposta**:
```json
{
  "success": true,
  "noticias": [
    {
      "id": 123,
      "titulo": "Market Update",
      "titulo_pt": "Atualização do Mercado",
      "link": "https://...",
      "fonte": "Bloomberg",
      "data_publicacao": "2025-10-15T10:30:00",
      "data_coleta": "2025-10-15T10:35:00",
      "descricao": "...",
      "descricao_pt": "..."
    }
  ]
}
```

#### `GET /api/fontes`
Lista fontes disponíveis com contagem.

**Resposta**:
```json
{
  "success": true,
  "fontes": [
    {"nome": "Bloomberg", "total": 45},
    {"nome": "InfoMoney", "total": 32}
  ]
}
```

#### `GET /api/stats`
Estatísticas gerais.

**Resposta**:
```json
{
  "success": true,
  "stats": {
    "total_noticias": 150,
    "total_fontes": 11,
    "ultima_atualizacao": "2025-10-15T10:30:00"
  }
}
```

#### `GET /api/uptime` 🆕
Status detalhado do sistema (CPU, RAM, disco, banco).

**Resposta**:
```json
{
  "success": true,
  "status": "online",
  "timestamp": "2025-10-15T13:40:00",
  "system": {
    "environment": "production",
    "platform": "Linux",
    "python_version": "3.11.0",
    "cpu_count": 2,
    "memory": {
      "total_mb": 512,
      "used_mb": 120,
      "percent": 23.4
    },
    "disk": {
      "total_gb": 10,
      "used_gb": 2.5,
      "percent": 25.0
    }
  },
  "database": {
    "path": "/app/noticias.db",
    "size_mb": 0.35,
    "storage_type": "ephemeral",
    "total_noticias": 150,
    "total_fontes": 11,
    "ultima_coleta": "2025-10-15T13:39:00"
  },
  "config": {
    "refresh_interval_seconds": 30,
    "max_age_hours": 24,
    "debug_mode": false
  }
}
```

---

## 🚀 Deploy na Railway

```bash
git add .
git commit -m "Deploy para Railway"
git push origin main
```

### 2. Deploy na Railway

1. Acesse [railway.app](https://railway.app) e faça login
2. **New Project** → **Deploy from GitHub repo**
3. Selecione o repositório
4. Aguarde o build (~1-2 min)
5. Acesse **Settings** → **Domains** → **Generate Domain**
6. Anote a URL: `https://seu-app.up.railway.app`

### 3. Configurar Variáveis de Ambiente

No dashboard Railway, vá em **Variables** e adicione:

```env
API_KEY=<gerar-chave-forte>
ALLOWED_ORIGINS=*.operebem.com,*.operebem.com.br
DEBUG=False
```

**Gerar chave forte**:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Configuração de CORS (ALLOWED_ORIGINS)**:
- `*.operebem.com,*.operebem.com.br` - Permite todos os subdomínios Operebem
- `https://terminal.operebem.com.br` - Permite apenas domínio específico
- `*` - Permite todas as origens (NÃO recomendado em produção)

### 4. Testar

```bash
# Health check (público)
curl https://seu-app.up.railway.app/api/health

# Stats (protegido)
curl -H "X-API-Key: sua-chave" \
  https://seu-app.up.railway.app/api/stats
```

### 5. (Opcional) Configurar Volume Persistente

Por padrão, o sistema usa **storage efêmero** (dados perdidos ao reiniciar).

Para persistência:
1. Railway Dashboard → **Settings** → **Volumes**
2. **Add Volume**
3. Mount path: `/data`
4. Size: 1 GB

O sistema detectará automaticamente e usará `/data/noticias.db`.

---

## 💻 Desenvolvimento Local

### Instalar

```bash
pip install -r requirements.txt
```

### Configurar

```bash
cp .env.example .env
# Edite .env e defina API_KEY
```

### Executar

```bash
# Coletor (modo contínuo)
python news_collector.py

# Coletor (uma vez)
python news_collector.py --refresh

# API
python api_server.py
```

### Acessar

- 🔌 API: http://localhost:5000
- ❤️ Health: http://localhost:5000/api/health

---

## 📊 Fontes RSS (11 total)

1. Bloomberg
2. The Wall Street Journal
3. MarketWatch
4. Yahoo Finance
5. Investing.com BR
6. OilPrice
7. Financial Times
8. CNBC
9. BNY Mellon
10. InfoMoney
11. Money Times

---

## 🗄️ Banco de Dados

**SQLite** com constraint `UNIQUE(link)` para prevenir duplicação.

| Campo | Descrição |
|-------|-----------|
| `titulo` | Original |
| `titulo_pt` | Traduzido (NULL se já PT) |
| `link` | URL única |
| `fonte` | Nome da fonte |
| `data_publicacao` | Do RSS |
| `data_coleta` | Timestamp local |
| `descricao` | Limpa (sem HTML) |
| `descricao_pt` | Traduzida |

---

## 🔧 Configuração

Variáveis de ambiente (`.env` ou Railway Variables):

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `API_KEY` | `dev-key-12345` | Chave de autenticação |
| `ALLOWED_ORIGINS` | `*` | Origens permitidas (CORS) |
| `DEBUG` | `False` | Modo debug |
| `REFRESH_INTERVAL` | `30` | Segundos entre coletas |
| `MAX_AGE_HOURS` | `24` | Retenção de notícias |

---

## 🐛 Troubleshooting

### Worker crashando: "unable to open database file"

**Causa**: Volume `/data` não configurado.

**Solução**: Sistema usa fallback automático para `/app/noticias.db` (efêmero). Para persistência, configure volume.

### API Key inválida

Verifique se a chave nas Variables da Railway está correta.

### Banco vazio

Aguarde 30s para primeira coleta. Veja logs: Railway Dashboard → Deployments → View Logs.

### CORS bloqueado

Se receber erro de CORS no navegador, verifique:
1. `ALLOWED_ORIGINS` está configurado no Railway
2. Seu domínio está na lista (ex: `*.operebem.com.br`)
3. Use wildcards para subdomínios: `*.operebem.com`

**⚠️ IMPORTANTE**: A API **bloqueia requisições diretas** de ferramentas como Postman, cURL, ReqBin, etc. Requisições devem vir de navegadores com header `Origin` válido. Isso é uma camada extra de segurança além da API Key.

---

## 🔐 Segurança

- ✅ **API Key** em todos os endpoints (exceto `/health`)
- ✅ **CORS restrito** por domínio (configurável via `ALLOWED_ORIGINS`)
- ✅ **Bloqueio de requisições diretas** - Apenas navegadores com `Origin` válido
- ✅ **Wildcards suportados**: `*.operebem.com` permite todos os subdomínios
- ✅ **`.env` no `.gitignore`** - Nunca commitar credenciais
- ✅ **HTTPS obrigatório** em produção
- ✅ **Validação de entrada** em todos os endpoints

### Como funciona a proteção CORS

A API implementa **duas camadas de segurança**:

1. **Validação de Origem (CORS)**: Bloqueia requisições sem header `Origin` ou com origem não autorizada
2. **API Key**: Valida a chave de autenticação em todos os endpoints

**Requisições bloqueadas:**
- ❌ Ferramentas HTTP diretas (Postman, cURL, ReqBin, wget)
- ❌ Scripts backend sem header `Origin`
- ❌ Origens não listadas em `ALLOWED_ORIGINS`

**Requisições permitidas:**
- ✅ Navegadores web de domínios autorizados
- ✅ Frontend hospedado em `*.operebem.com` ou `*.operebem.com.br`
- ✅ Endpoint `/health` (sem restrições para monitoramento)

### Exemplo de Configuração CORS

```env
# Permite apenas domínios Operebem
ALLOWED_ORIGINS=*.operebem.com,*.operebem.com.br

# Permite domínios específicos
ALLOWED_ORIGINS=https://terminal.operebem.com.br,https://group.operebem.com.br

# Desenvolvimento local + produção
ALLOWED_ORIGINS=http://localhost:3000,*.operebem.com.br
```

---

## 📁 Estrutura

```
RSS-NEWS/
├── api_server.py          # API REST Flask
├── news_collector.py      # Coletor RSS
├── config.py              # Configurações
├── requirements.txt       # Dependências
├── Procfile              # Railway config
├── railway.json          # Railway settings
├── runtime.txt           # Python 3.11
└── README.md             # Este arquivo
```

---

## 📊 Status

- ✅ **Versão**: 2.0
- ✅ **Deploy**: Railway
- ✅ **URL**: https://news-operebem.up.railway.app
- ✅ **Última atualização**: 15/10/2025

---

**Desenvolvido com ❤️ para Operebem**
