#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Coleta e Exibição de Notícias Financeiras via RSS
Autor: Sistema Automatizado
Data: 2025
"""

import sqlite3
import feedparser
import time
import argparse
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
import sys
import re
from html import unescape
from deep_translator import GoogleTranslator
from langdetect import detect, LangDetectException
import os

# Importar configurações
try:
    from config import DB_NAME, REFRESH_INTERVAL, MAX_AGE_HOURS
except ImportError:
    # Fallback para desenvolvimento sem config.py
    DB_NAME = "noticias.db"
    REFRESH_INTERVAL = 30
    MAX_AGE_HOURS = 24


# ==================== CONFIGURAÇÕES ====================

# Lista de feeds RSS financeiros
# Nota: URLs do Banco Central usam ano dinâmico (atualizado automaticamente)
RSS_FEEDS = [
    {"url": "https://feeds.bloomberg.com/markets/news.rss", "fonte": "Bloomberg"},
    {"url": "https://feeds.content.dowjones.io/public/rss/RSSMarketsMain", "fonte": "The Wall Street Journal"},
    {"url": "https://finance.yahoo.com/news/rssindex", "fonte": "Yahoo Finance"},
    {"url": "https://br.investing.com/rss/news.rss", "fonte": "Investing.com BR"},
    {"url": "https://oilprice.com/rss/main", "fonte": "OilPrice"},
    {"url": "https://www.ft.com/rss/home/uk", "fonte": "Financial Times"},
    {"url": "https://www.cnbc.com/id/100003114/device/rss/rss.html", "fonte": "CNBC"},
    {"url": "https://www.infomoney.com.br/feed/", "fonte": "InfoMoney"},
    {"url": "https://www.moneytimes.com.br/feed/", "fonte": "Money Times"},
    # Banco Central do Brasil (ano dinâmico)
    {"url": f"https://www.bcb.gov.br/api/feed/sitebcb/sitefeeds/noticias?ano={datetime.now().year}", "fonte": "Banco Central - Notícias"},
    {"url": f"https://www.bcb.gov.br/api/feed/app/demaisnormativos/atosecomunicados?ano={datetime.now().year}", "fonte": "Banco Central - Comunicados"},
    {"url": f"https://www.bcb.gov.br/api/feed/sitebcb/sitefeeds/notasImprensa?ano={datetime.now().year}", "fonte": "Banco Central - Notas à Imprensa"},
    # Criptomoedas
    {"url": "https://www.coindesk.com/arc/outboundfeeds/rss/", "fonte": "CoinDesk"},
]


# ==================== BANCO DE DADOS ====================

def criar_banco_dados():
    """
    Cria a estrutura do banco de dados SQLite se não existir.
    Tabela: noticias (id, titulo, link, fonte, data_publicacao, descricao, data_coleta, titulo_pt, descricao_pt)
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS noticias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            link TEXT UNIQUE NOT NULL,
            fonte TEXT NOT NULL,
            data_publicacao TEXT,
            descricao TEXT,
            data_coleta TEXT NOT NULL,
            titulo_pt TEXT,
            descricao_pt TEXT
        )
    """)
    
    # Criar índice para melhorar performance nas buscas
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_link ON noticias(link)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_data_publicacao ON noticias(data_publicacao)
    """)
    
    conn.commit()
    conn.close()
    print(f"✓ Banco de dados '{DB_NAME}' inicializado com sucesso.")


def limpar_noticias_antigas():
    """
    Remove notícias com mais de 24 horas do banco de dados.
    Usa a data de COLETA (não publicação) para determinar quais notícias remover.
    Isso evita problemas com feeds RSS que têm datas incorretas.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Calcular timestamp de 24 horas atrás em UTC
    limite_tempo = datetime.now(timezone.utc) - timedelta(hours=MAX_AGE_HOURS)
    limite_str = limite_tempo.isoformat()
    
    # Deletar notícias antigas baseado na data de COLETA
    cursor.execute("""
        DELETE FROM noticias 
        WHERE data_coleta < ? OR data_coleta IS NULL
    """, (limite_str,))
    
    deletadas = cursor.rowcount
    conn.commit()
    conn.close()
    
    if deletadas > 0:
        print(f"🗑️  {deletadas} notícia(s) antiga(s) removida(s).")
    
    return deletadas


def inserir_noticia(titulo: str, link: str, fonte: str, data_pub: Optional[str], descricao: str) -> bool:
    """
    Insere uma notícia no banco de dados se ela não existir.
    Traduz título e descrição automaticamente se não estiverem em português.
    Retorna True se inseriu, False se já existia.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # Data de coleta em formato ISO com timezone UTC
        data_coleta = datetime.now(timezone.utc).isoformat()
        
        # Detectar idioma e traduzir apenas se necessário
        titulo_pt = None
        descricao_pt = None
        
        idioma_titulo = detectar_idioma(titulo)
        if idioma_titulo and idioma_titulo != 'pt':
            titulo_pt = traduzir_texto(titulo)
        
        if descricao:
            idioma_desc = detectar_idioma(descricao)
            if idioma_desc and idioma_desc != 'pt':
                descricao_pt = traduzir_texto(descricao)
        
        cursor.execute("""
            INSERT INTO noticias (titulo, link, fonte, data_publicacao, descricao, data_coleta, titulo_pt, descricao_pt)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (titulo, link, fonte, data_pub, descricao, data_coleta, titulo_pt, descricao_pt))
        
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        # Link já existe no banco - DUPLICAÇÃO PREVENIDA
        conn.close()
        return False


def obter_todas_noticias() -> List[Dict]:
    """
    Retorna todas as notícias do banco ordenadas da mais recente para a mais antiga.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT titulo, link, fonte, data_publicacao, descricao, data_coleta, titulo_pt, descricao_pt
        FROM noticias
        ORDER BY data_publicacao DESC
    """)
    
    noticias = []
    for row in cursor.fetchall():
        noticias.append({
            "titulo": row[0],
            "link": row[1],
            "fonte": row[2],
            "data_publicacao": row[3],
            "descricao": row[4],
            "data_coleta": row[5],
            "titulo_pt": row[6],
            "descricao_pt": row[7]
        })
    
    conn.close()
    return noticias


# ==================== LIMPEZA E TRADUÇÃO ====================

def limpar_html(texto: str) -> str:
    """
    Remove todas as tags HTML e limpa o texto.
    """
    if not texto:
        return ""
    
    # Decodificar entidades HTML
    texto = unescape(texto)
    
    # Remover tags HTML
    texto = re.sub(r'<[^>]+>', '', texto)
    
    # Remover múltiplos espaços
    texto = re.sub(r'\s+', ' ', texto)
    
    # Limitar tamanho
    if len(texto) > 500:
        texto = texto[:497] + "..."
    
    return texto.strip()


def detectar_idioma(texto: str) -> Optional[str]:
    """
    Detecta o idioma do texto usando langdetect.
    Retorna código do idioma (ex: 'pt', 'en') ou None se falhar.
    """
    if not texto or len(texto.strip()) < 10:
        return None
    
    try:
        idioma = detect(texto)
        return idioma
    except LangDetectException:
        return None


def traduzir_texto(texto: str, idioma_origem: str = 'auto') -> Optional[str]:
    """
    Traduz texto para português usando Google Translator.
    Retorna a tradução ou None se houver erro.
    IMPORTANTE: Só deve ser chamado se o texto NÃO estiver em português.
    """
    if not texto or len(texto.strip()) < 3:
        return None
    
    try:
        translator = GoogleTranslator(source=idioma_origem, target='pt')
        traducao = translator.translate(texto)
        return traducao if traducao and traducao != texto else None
    except Exception as e:
        # Se falhar, retorna None (usará o original)
        print(f"⚠️  Erro na tradução: {str(e)}")
        return None


# ==================== COLETA DE RSS ====================

def parsear_data(entry) -> Optional[str]:
    """
    Extrai e converte a data de publicação do feed RSS para formato ISO com timezone UTC.
    """
    try:
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            # Converter para UTC timezone-aware datetime
            dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            return dt.isoformat()
        elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            # Converter para UTC timezone-aware datetime
            dt = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
            return dt.isoformat()
    except Exception:
        pass
    
    # Se não conseguir parsear, usar data atual em UTC
    return datetime.now(timezone.utc).isoformat()


def coletar_feed(feed_url: str, fonte: str) -> int:
    """
    Coleta notícias de um feed RSS específico.
    Retorna o número de notícias novas inseridas.
    """
    try:
        feed = feedparser.parse(feed_url)
        novas = 0
        
        for entry in feed.entries:
            titulo = entry.get('title', 'Sem título')
            link = entry.get('link', '')
            descricao = entry.get('summary', entry.get('description', ''))
            
            # Limpar HTML da descrição
            descricao = limpar_html(descricao)
            
            data_pub = parsear_data(entry)
            
            # Tentar inserir no banco
            if link and inserir_noticia(titulo, link, fonte, data_pub, descricao):
                novas += 1
        
        return novas
    
    except Exception as e:
        print(f"⚠️  Erro ao coletar {fonte}: {str(e)}")
        return 0


def coletar_todos_feeds() -> int:
    """
    Coleta notícias de todos os feeds RSS configurados.
    Retorna o total de notícias novas coletadas.
    """
    print("\n" + "="*70)
    print("🔄 INICIANDO COLETA DE NOTÍCIAS...")
    print("="*70)
    
    total_novas = 0
    
    for feed in RSS_FEEDS:
        print(f"📡 Coletando: {feed['fonte']}...", end=" ")
        sys.stdout.flush()
        
        novas = coletar_feed(feed['url'], feed['fonte'])
        total_novas += novas
        
        if novas > 0:
            print(f"✓ {novas} nova(s)")
        else:
            print("✓ Nenhuma nova")
    
    print(f"\n✅ Coleta finalizada: {total_novas} notícia(s) nova(s) no total.")
    
    # Limpar notícias antigas após coletar
    limpar_noticias_antigas()
    
    return total_novas


# ==================== EXIBIÇÃO ====================

def formatar_data(data_iso: str) -> str:
    """
    Formata a data ISO para exibição amigável.
    """
    try:
        dt = datetime.fromisoformat(data_iso)
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return "Data desconhecida"


def exibir_noticias():
    """
    Exibe todas as notícias do banco de forma formatada no terminal.
    """
    noticias = obter_todas_noticias()
    
    print("\n" + "="*70)
    print(f"📰 NOTÍCIAS FINANCEIRAS (Últimas 24 horas)")
    print(f"📊 Total: {len(noticias)} notícia(s)")
    print("="*70 + "\n")
    
    if not noticias:
        print("ℹ️  Nenhuma notícia disponível no momento.\n")
        return
    
    for i, noticia in enumerate(noticias, 1):
        data_formatada = formatar_data(noticia['data_publicacao'])
        
        print(f"[{noticia['fonte']}] {data_formatada}")
        print(f"📌 {noticia['titulo']}")
        print(f"🔗 {noticia['link']}")
        
        if noticia['descricao']:
            print(f"💬 {noticia['descricao']}")
        
        print("-" * 70)
        
        if i < len(noticias):
            print()  # Linha em branco entre notícias
    
    print()


# ==================== MAIN ====================

def main():
    """
    Função principal que gerencia o fluxo do programa.
    """
    parser = argparse.ArgumentParser(
        description="Sistema de Coleta e Exibição de Notícias Financeiras via RSS"
    )
    parser.add_argument(
        '--refresh',
        action='store_true',
        help='Executa apenas uma coleta e exibição (sem loop contínuo)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=REFRESH_INTERVAL,
        help=f'Intervalo entre coletas em segundos (padrão: {REFRESH_INTERVAL}s)'
    )
    
    args = parser.parse_args()
    
    # Inicializar banco de dados
    criar_banco_dados()
    
    if args.refresh:
        # Modo manual: uma coleta e exibição
        print("\n🔧 Modo: Atualização Manual")
        coletar_todos_feeds()
        exibir_noticias()
        print("✓ Atualização concluída.\n")
    else:
        # Modo contínuo: loop infinito
        print("\n🚀 Modo: Coleta Contínua")
        print(f"⏱️  Intervalo: {args.interval} segundos")
        print("⚠️  Pressione Ctrl+C para interromper\n")
        
        try:
            while True:
                coletar_todos_feeds()
                # Não exibir notícias em produção (economiza CPU/memória)
                if not os.getenv('RAILWAY_ENVIRONMENT'):
                    exibir_noticias()
                
                print(f"⏳ Aguardando {args.interval} segundos até a próxima coleta...")
                print("="*70 + "\n")
                
                time.sleep(args.interval)
        
        except KeyboardInterrupt:
            print("\n\n⛔ Programa interrompido pelo usuário.")
            print("✓ Encerrando de forma segura...\n")
            sys.exit(0)


if __name__ == "__main__":
    main()
