"""
Configurações do sistema
Gerencia diferentes ambientes (desenvolvimento vs produção)
"""

import os
import logging

# Detectar ambiente
IS_PRODUCTION = os.getenv('RAILWAY_ENVIRONMENT') is not None

# Configurar logging
if IS_PRODUCTION:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
else:
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

logger = logging.getLogger(__name__)

# Configuração do banco de dados
if IS_PRODUCTION:
    # Produção (Railway): usar sistema de arquivos local (mesmo container)
    DB_NAME = '/app/noticias.db'
    logger.info("🌐 Ambiente: PRODUÇÃO (Railway)")
    logger.info(f"💾 Banco de dados: {DB_NAME}")
    logger.info("ℹ️  Coletor e API no mesmo container - banco compartilhado")
else:
    # Desenvolvimento: usar pasta local
    DB_NAME = 'noticias.db'
    logger.info("🔧 Ambiente: DESENVOLVIMENTO (Local)")
    logger.info(f"💾 Banco de dados: {DB_NAME}")

# Outras configurações
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
API_KEY = os.getenv('API_KEY', 'dev-key-12345')
PORT = int(os.getenv('PORT', 5000))

# Configurações do coletor
REFRESH_INTERVAL = int(os.getenv('REFRESH_INTERVAL', '30'))  # segundos
MAX_AGE_HOURS = int(os.getenv('MAX_AGE_HOURS', '24'))  # horas

# Configurações de performance
MAX_WORKERS = int(os.getenv('MAX_WORKERS', '1'))  # Gunicorn workers
THREADS_PER_WORKER = int(os.getenv('THREADS_PER_WORKER', '2'))  # Threads por worker
