#!/bin/bash
# Script para iniciar coletor em background e API em foreground

echo "🚀 Iniciando sistema unificado..."

# Iniciar coletor em background
echo "📡 Iniciando coletor de notícias..."
python news_collector.py &
COLLECTOR_PID=$!

# Aguardar 5 segundos para primeira coleta
echo "⏳ Aguardando primeira coleta..."
sleep 5

# Iniciar API em foreground
echo "🌐 Iniciando API server..."
gunicorn api_server:app \
    --bind 0.0.0.0:${PORT:-8080} \
    --workers 1 \
    --threads 2 \
    --timeout 120 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --access-logfile - \
    --error-logfile -

# Se API cair, matar coletor também
kill $COLLECTOR_PID 2>/dev/null
