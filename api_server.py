#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API REST para servir notícias financeiras do banco SQLite
Servidor Flask com CORS e autenticação via API Key
"""

from flask import Flask, jsonify, request, make_response
import sqlite3
from datetime import datetime
from typing import List, Dict
from functools import wraps
import os
import re
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

app = Flask(__name__)

# Configuração de CORS será feita via middleware customizado

# Importar configurações
try:
    from config import DB_NAME, API_KEY, PORT, DEBUG
except ImportError:
    # Fallback para desenvolvimento sem config.py
    DB_NAME = "noticias.db"
    API_KEY = os.getenv('API_KEY', 'dev-key-12345')
    PORT = int(os.getenv('PORT', 5000))
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# Configuração de origens permitidas (CORS)
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', '*').split(',')
ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS]

# Log de configuração CORS
print(f"🔒 CORS configurado com origens permitidas: {ALLOWED_ORIGINS}")


def is_origin_allowed(origin):
    """
    Verifica se a origem é permitida.
    Suporta wildcards (*.operebem.com) e domínios exatos.
    """
    if not origin:
        return False
    
    # Se permitir todas as origens
    if '*' in ALLOWED_ORIGINS:
        return True
    
    # Verificar domínios exatos
    if origin in ALLOWED_ORIGINS:
        return True
    
    # Verificar wildcards
    for allowed in ALLOWED_ORIGINS:
        if '*' in allowed:
            # Converter wildcard para regex
            # *.operebem.com -> ^https?://.*\.operebem\.com$
            pattern = allowed.replace('.', '\\.').replace('*', '.*')
            # Adicionar protocolo se não tiver
            if not pattern.startswith('http'):
                pattern = f'^https?://{pattern}$'
            else:
                pattern = f'^{pattern}$'
            
            if re.match(pattern, origin, re.IGNORECASE):
                return True
    
    return False


@app.after_request
def add_cors_headers(response):
    """
    Adiciona headers CORS customizados baseado nas origens permitidas.
    """
    origin = request.headers.get('Origin')
    
    if is_origin_allowed(origin):
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-API-Key'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
    
    return response


@app.route('/api/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    """
    Responde a requisições OPTIONS (preflight CORS).
    """
    return '', 204


def get_db_connection():
    """Cria conexão com o banco de dados SQLite"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # Permite acessar colunas por nome
    return conn


def require_api_key(f):
    """
    Decorator para proteger endpoints com API Key.
    A chave deve ser enviada no header 'X-API-Key' ou como query param 'api_key'.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Verificar header
        api_key = request.headers.get('X-API-Key')
        
        # Se não estiver no header, verificar query param
        if not api_key:
            api_key = request.args.get('api_key')
        
        # Validar API Key
        if not api_key or api_key != API_KEY:
            return jsonify({
                'success': False,
                'error': 'API Key inválida ou ausente',
                'message': 'Forneça uma API Key válida no header X-API-Key ou query param api_key'
            }), 401
        
        return f(*args, **kwargs)
    return decorated_function


@app.route('/api/noticias', methods=['GET'])
@require_api_key
def get_noticias():
    """
    Retorna todas as notícias ordenadas da mais recente para a mais antiga.
    Query params opcionais:
    - fonte: filtrar por fonte específica
    - limit: limitar número de resultados
    """
    try:
        fonte = request.args.get('fonte')
        limit = request.args.get('limit', type=int)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT id, titulo, link, fonte, data_publicacao, descricao, data_coleta, titulo_pt, descricao_pt
            FROM noticias
        """
        
        params = []
        
        if fonte:
            query += " WHERE fonte = ?"
            params.append(fonte)
        
        query += " ORDER BY data_publicacao DESC"
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        noticias = []
        for row in rows:
            noticias.append({
                'id': row['id'],
                'titulo': row['titulo'],
                'link': row['link'],
                'fonte': row['fonte'],
                'data_publicacao': row['data_publicacao'],
                'descricao': row['descricao'],
                'data_coleta': row['data_coleta'],
                'titulo_pt': row['titulo_pt'],
                'descricao_pt': row['descricao_pt']
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'total': len(noticias),
            'noticias': noticias
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/fontes', methods=['GET'])
@require_api_key
def get_fontes():
    """Retorna lista de todas as fontes disponíveis com contagem de notícias"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT fonte, COUNT(*) as total
            FROM noticias
            GROUP BY fonte
            ORDER BY total DESC
        """)
        
        rows = cursor.fetchall()
        
        fontes = []
        for row in rows:
            fontes.append({
                'nome': row['fonte'],
                'total': row['total']
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'fontes': fontes
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/stats', methods=['GET'])
@require_api_key
def get_stats():
    """Retorna estatísticas gerais do sistema"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Total de notícias
        cursor.execute("SELECT COUNT(*) as total FROM noticias")
        total = cursor.fetchone()['total']
        
        # Notícia mais recente (usar data_coleta que é sempre confiável)
        cursor.execute("""
            SELECT data_coleta 
            FROM noticias 
            ORDER BY data_coleta DESC 
            LIMIT 1
        """)
        ultima_row = cursor.fetchone()
        ultima_atualizacao = ultima_row['data_coleta'] if ultima_row else None
        
        # Total por fonte
        cursor.execute("""
            SELECT COUNT(DISTINCT fonte) as total_fontes
            FROM noticias
        """)
        total_fontes = cursor.fetchone()['total_fontes']
        
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_noticias': total,
                'total_fontes': total_fontes,
                'ultima_atualizacao': ultima_atualizacao
            }
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Endpoint de health check público"""
    return jsonify({
        'success': True,
        'status': 'online',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/uptime', methods=['GET'])
@require_api_key
def uptime_status():
    """
    Endpoint de status detalhado do sistema (requer API Key)
    Retorna informações sobre banco de dados, última coleta, sistema, etc.
    """
    try:
        import os
        import platform
        import psutil
        from config import DB_NAME, IS_PRODUCTION, REFRESH_INTERVAL, MAX_AGE_HOURS
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Estatísticas do banco
        cursor.execute("SELECT COUNT(*) FROM noticias")
        total_noticias = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT fonte) FROM noticias")
        total_fontes = cursor.fetchone()[0]
        
        cursor.execute("SELECT data_coleta FROM noticias ORDER BY data_coleta DESC LIMIT 1")
        ultima_coleta = cursor.fetchone()
        ultima_coleta = ultima_coleta[0] if ultima_coleta else None
        
        cursor.execute("SELECT data_publicacao FROM noticias ORDER BY data_publicacao DESC LIMIT 1")
        ultima_publicacao = cursor.fetchone()
        ultima_publicacao = ultima_publicacao[0] if ultima_publicacao else None
        
        # Informações do banco de dados
        db_size = os.path.getsize(DB_NAME) if os.path.exists(DB_NAME) else 0
        db_size_mb = round(db_size / (1024 * 1024), 2)
        
        # Verificar tipo de storage
        storage_type = "ephemeral"
        if '/data/' in DB_NAME:
            storage_type = "persistent_volume"
        elif '/app/' in DB_NAME:
            storage_type = "ephemeral"
        else:
            storage_type = "local"
        
        # Informações do sistema
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        conn.close()
        
        return jsonify({
            'success': True,
            'status': 'online',
            'timestamp': datetime.now().isoformat(),
            'system': {
                'environment': 'production' if IS_PRODUCTION else 'development',
                'platform': platform.system(),
                'python_version': platform.python_version(),
                'cpu_count': psutil.cpu_count(),
                'memory': {
                    'total_mb': round(memory.total / (1024 * 1024), 2),
                    'used_mb': round(memory.used / (1024 * 1024), 2),
                    'percent': memory.percent
                },
                'disk': {
                    'total_gb': round(disk.total / (1024 * 1024 * 1024), 2),
                    'used_gb': round(disk.used / (1024 * 1024 * 1024), 2),
                    'percent': disk.percent
                }
            },
            'database': {
                'path': DB_NAME,
                'size_mb': db_size_mb,
                'storage_type': storage_type,
                'total_noticias': total_noticias,
                'total_fontes': total_fontes,
                'ultima_coleta': ultima_coleta,
                'ultima_publicacao': ultima_publicacao
            },
            'config': {
                'refresh_interval_seconds': REFRESH_INTERVAL,
                'max_age_hours': MAX_AGE_HOURS,
                'debug_mode': DEBUG
            }
        })
    
    except ImportError:
        # psutil não instalado - versão simplificada
        try:
            import os
            from config import DB_NAME, IS_PRODUCTION, REFRESH_INTERVAL, MAX_AGE_HOURS
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM noticias")
            total_noticias = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT fonte) FROM noticias")
            total_fontes = cursor.fetchone()[0]
            
            cursor.execute("SELECT data_coleta FROM noticias ORDER BY data_coleta DESC LIMIT 1")
            ultima_coleta = cursor.fetchone()
            ultima_coleta = ultima_coleta[0] if ultima_coleta else None
            
            db_size = os.path.getsize(DB_NAME) if os.path.exists(DB_NAME) else 0
            db_size_mb = round(db_size / (1024 * 1024), 2)
            
            storage_type = "ephemeral"
            if '/data/' in DB_NAME:
                storage_type = "persistent_volume"
            elif '/app/' in DB_NAME:
                storage_type = "ephemeral"
            
            conn.close()
            
            return jsonify({
                'success': True,
                'status': 'online',
                'timestamp': datetime.now().isoformat(),
                'system': {
                    'environment': 'production' if IS_PRODUCTION else 'development'
                },
                'database': {
                    'path': DB_NAME,
                    'size_mb': db_size_mb,
                    'storage_type': storage_type,
                    'total_noticias': total_noticias,
                    'total_fontes': total_fontes,
                    'ultima_coleta': ultima_coleta
                },
                'config': {
                    'refresh_interval_seconds': REFRESH_INTERVAL,
                    'max_age_hours': MAX_AGE_HOURS
                }
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    import logging
    
    # Configurar logging
    if DEBUG:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    
    print("🚀 Servidor API iniciado")
    print(f"🔐 Autenticação: API Key ativa")
    print(f"🔑 API Key: {API_KEY[:8]}...")
    print(f"🌐 Porta: {PORT}")
    print(f"🔧 Debug: {DEBUG}")
    print("\n📡 Endpoints disponíveis:")
    print("   - GET /api/noticias  [🔒 Protegido]")
    print("   - GET /api/fontes    [🔒 Protegido]")
    print("   - GET /api/stats     [🔒 Protegido]")
    print("   - GET /api/uptime    [🔒 Protegido] - Status detalhado")
    print("   - GET /api/health    [✅ Público] - Health check")
    print("\n📝 Como usar:")
    print("   Header: X-API-Key: sua-chave")
    print("   ou Query: ?api_key=sua-chave")
    print("\n⚠️  Pressione Ctrl+C para parar o servidor\n")
    
    app.run(host='0.0.0.0', port=PORT, debug=DEBUG)
