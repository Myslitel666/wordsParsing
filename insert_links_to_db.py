import re
import sqlite3
import requests
import time
import socket
from urllib.parse import urljoin, urlparse
from blacklist import BLACKLIST
import sys
import traceback

# ============================================================
# 🔥 ФУНКЦИЯ ДЛЯ ПОДРОБНОЙ ОТЛАДКИ (ПИШЕТ В ФАЙЛ И В КОНСОЛЬ)
# ============================================================
DEBUG_FILE = 'debug_collect_links.log'

def debug_log(message, data=None, force_print=True):
    """Записывает отладочную информацию в файл и в консоль."""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    
    # Формируем строку
    if data is not None:
        if isinstance(data, dict):
            data_str = '\n'.join([f"      {k}: {v}" for k, v in data.items()])
        else:
            data_str = f"   {data}"
        full_msg = f"[{timestamp}] {message}\n{data_str}\n"
    else:
        full_msg = f"[{timestamp}] {message}\n"
    
    # Пишем в файл
    try:
        with open(DEBUG_FILE, 'a', encoding='utf-8') as f:
            f.write(full_msg)
    except:
        pass
    
    # Печатаем в консоль
    if force_print:
        print(full_msg.strip())

# Конфигурация
DELAY_BETWEEN_REQUESTS = 1  # Задержка между запросами (сек)
LOG_FILE = 'collected_links.log'
DB_PATH = 'words.db'

def wait_for_internet(host='8.8.8.8', port=53, timeout=3):
    """Проверяет доступность интернета и ждёт, пока он появится."""
    while True:
        try:
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            return True
        except socket.error:
            print("🌐 Нет интернета. Жду 8 секунд...")
            time.sleep(8)

def log_link(link):
    """Записывает ссылку в лог-файл."""
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{link}\n")
    except Exception as e:
        print(f"⚠️ Ошибка записи в лог: {e}")

def is_blacklisted(url):
    """Проверяет, содержит ли URL путь из чёрного списка для этого домена."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    
    if domain.startswith('www.'):
        domain = domain[4:]
    
    path = parsed.path.lower().rstrip('/')
    
    if domain in BLACKLIST:
        for blocked in BLACKLIST[domain]:
            blocked_clean = blocked.rstrip('/')
            if blocked_clean in path:
                return True
    
    return False

def extract_links_from_url(url, base_url=None):
    """
    Извлекает все ссылки со страницы.
    Возвращает список абсолютных URL.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, timeout=30, headers=headers)
        response.raise_for_status()
        html = response.text
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка загрузки страницы: {e}")
        return []

    if base_url is None:
        base_url = url

    pattern = re.compile(r'href\s*=\s*["\']?([^"\'\s>]+)["\']?', re.IGNORECASE)
    raw_links = pattern.findall(html)
    
    SKIP_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.webp',
                       '.json', '.xml', '.css', '.js', '.pdf', '.zip', '.rar',
                       '.mp4', '.mp3', '.avi', '.mkv', '.exe', '.dmg', '.woff', '.woff2')
    
    absolute_links = []
    seen = set()
    parsed_base = urlparse(base_url)
    
    for raw_link in raw_links:
        if not raw_link or raw_link.startswith('#') or raw_link.startswith('javascript:'):
            continue
            
        full_url = urljoin(base_url, raw_link)
        
        if '#' in full_url:
            full_url = full_url.split('#')[0]
        
        if full_url.lower().endswith(SKIP_EXTENSIONS):
            continue
        
        if is_blacklisted(full_url):
            continue
        
        parsed_full = urlparse(full_url)
        if parsed_base.netloc == parsed_full.netloc and full_url not in seen:
            seen.add(full_url)
            absolute_links.append(full_url)
    
    return absolute_links

def init_database(db_path=DB_PATH):
    """Создаёт таблицу Links с полем processed."""
    conn = sqlite3.connect(db_path, timeout=10)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            processed INTEGER DEFAULT 0,
            collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Добавляем индекс для быстрого поиска
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_links_processed ON Links(processed)')
    
    conn.commit()
    conn.close()
    print("✅ Таблица Links создана/проверена (с полем processed)")

def save_links_to_db(conn, links):
    """Сохраняет ссылки в базу (только новые, processed=0)."""
    if not links:
        return 0
    
    cursor = conn.cursor()
    inserted = 0
    counter = 0
    
    for link in links:
        try:
            # Вставляем только если ссылки нет
            cursor.execute('INSERT OR IGNORE INTO Links (url, processed) VALUES (?, 0)', (link,))
            if cursor.rowcount > 0:
                inserted += 1
                counter += 1
                log_link(link)
                
                if counter >= 1000:
                    conn.commit()
                    counter = 0
        except sqlite3.OperationalError as e:
            print(f"⚠️ Ошибка вставки: {e}")
    
    if counter > 0:
        conn.commit()
    
    print(f"   💾 Вставлено новых ссылок: {inserted}")
    return inserted

def get_unprocessed_links(conn, limit=100):
    """Возвращает список необработанных ссылок."""
    cursor = conn.cursor()
    cursor.execute('SELECT url FROM Links WHERE processed = 0 LIMIT ?', (limit,))
    return [row[0] for row in cursor.fetchall()]

def mark_as_processed(conn, url):
    """Помечает ссылку как обработанную."""
    cursor = conn.cursor()
    cursor.execute('UPDATE Links SET processed = 1 WHERE url = ?', (url,))
    conn.commit()

def is_link_processed(conn, url):
    """Проверяет, есть ли ссылка в таблице Links."""
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM Links WHERE url = ?', (url,))
    return cursor.fetchone() is not None

def collect_links():
    """Основная функция сбора ссылок (глубина 3) с ИСПРАВЛЕННОЙ ПРОВЕРКОЙ."""
    URLS_TO_PARSE = ['https://azbyka.ru/otechnik/']
    
    with open(DEBUG_FILE, 'w', encoding='utf-8') as f:
        f.write(f"=== ОТЛАДОЧНЫЙ ЛОГ ЗАПУСКА {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
    
    debug_log("🚀 НАЧАЛО СБОРА ССЫЛОК (глубина 3)")
    debug_log(f"📌 URLS_TO_PARSE: {URLS_TO_PARSE}")
    
    init_database()
    conn = sqlite3.connect(DB_PATH, timeout=10)
    
    all_links = set()
    queue = list(URLS_TO_PARSE)
    page_count = 0
    current_depth = 1
    next_level_urls = []
    next_next_level_urls = []
    
    print("🚀 Начинаем сбор ссылок (глубина 3)...")
    wait_for_internet()
    
    iteration = 0
    while queue:
        iteration += 1
        url = queue.pop(0)
        
        # ═══════════════════════════════════════
        # 🔥 ИСПРАВЛЕННАЯ ПРОВЕРКА
        # ═══════════════════════════════════════
        cursor = conn.cursor()
        cursor.execute('SELECT processed FROM Links WHERE url = ?', (url,))
        row = cursor.fetchone()
        
        if row is not None and row[0] == 1:
            debug_log(f"⏭️ ПРОПУСКАЮ (уже обработана)", {"url": url})
            print(f"⏭️ Пропускаю (уже обработана): {url}")
            continue
        elif row is not None and row[0] == 0:
            debug_log(f"🔄 ОБРАБАТЫВАЮ (есть в базе, не обработана)", {"url": url})
            print(f"🔄 Обрабатываю (есть в базе, не обработана): {url}")
        else:
            debug_log(f"🆕 НОВАЯ ССЫЛКА (нет в базе)", {"url": url})
            print(f"🆕 Новая ссылка: {url}")
        
        # ═══════════════════════════════════════
        # 🔥 ОСНОВНАЯ ОБРАБОТКА
        # ═══════════════════════════════════════
        page_count += 1
        print(f"\n🔗 [{page_count}] Собираю ссылки с: {url} (глубина {current_depth})")
        
        wait_for_internet()
        links = extract_links_from_url(url)
        
        if links:
            print(f"   📝 Найдено ссылок: {len(links)}")
            
            new_links = []
            for link in links:
                # Проверяем, есть ли ссылка в базе (неважно, processed или нет)
                cursor = conn.cursor()
                cursor.execute('SELECT 1 FROM Links WHERE url = ?', (link,))
                if cursor.fetchone() is None:
                    new_links.append(link)
                    all_links.add(link)
                    
                    if current_depth == 1:
                        next_level_urls.append(link)
                    elif current_depth == 2:
                        next_next_level_urls.append(link)
            
            print(f"   ➡️ Новых ссылок: {len(new_links)}")
            print(f"   📊 Всего уникальных ссылок собрано: {len(all_links)}")
            print(f"   📊 Очередь уровня 2: {len(next_level_urls)} ссылок")
            print(f"   📊 Очередь уровня 3: {len(next_next_level_urls)} ссылок")
            
            if new_links:
                save_links_to_db(conn, new_links)
            
            # Помечаем текущую страницу как обработанную
            mark_as_processed(conn, url)
            print(f"   ✅ Страница помечена как обработанная")
        else:
            print("   ❌ Ссылок не найдено")
            mark_as_processed(conn, url)
        
        # ═══════════════════════════════════════
        # 🔥 ПЕРЕХОД НА СЛЕДУЮЩИЙ УРОВЕНЬ
        # ═══════════════════════════════════════
        if not queue:
            if current_depth == 1 and next_level_urls:
                print(f"\n📂 ПЕРЕХОДИМ на глубину 2...")
                print(f"   ➡️ Найдено ссылок для уровня 2: {len(next_level_urls)}")
                queue = list(next_level_urls)
                next_level_urls = []
                current_depth = 2
                print(f"   ✅ Теперь глубина: {current_depth}, очередь: {len(queue)}")
                
            elif current_depth == 2 and next_next_level_urls:
                print(f"\n📂 ПЕРЕХОДИМ на глубину 3...")
                print(f"   ➡️ Найдено ссылок для уровня 3: {len(next_next_level_urls)}")
                queue = list(next_next_level_urls)
                next_next_level_urls = []
                current_depth = 3
                print(f"   ✅ Теперь глубина: {current_depth}, очередь: {len(queue)}")
                
            else:
                print(f"⚠️ НЕТ ССЫЛОК ДЛЯ ПЕРЕХОДА!")
                print(f"   current_depth={current_depth}")
                print(f"   next_level_urls={len(next_level_urls)}")
                print(f"   next_next_level_urls={len(next_next_level_urls)}")
        else:
            print(f"⏳ В очереди осталось {len(queue)} ссылок")
        
        time.sleep(DELAY_BETWEEN_REQUESTS)
    
    conn.close()
    
    print(f"\n{'='*60}")
    print(f"✅ ОБРАБОТАНО СТРАНИЦ: {page_count}")
    print(f"✅ ВСЕГО УНИКАЛЬНЫХ ССЫЛОК СОБРАНО: {len(all_links)}")

def get_total_links_count(db_path=DB_PATH):
    """Возвращает общее количество ссылок в базе."""
    conn = sqlite3.connect(db_path, timeout=10)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM Links')
    count = cursor.fetchone()[0]
    conn.close()
    return count

def show_sample_links(db_path=DB_PATH, limit=10):
    """Показывает примеры ссылок из базы."""
    conn = sqlite3.connect(db_path, timeout=10)
    cursor = conn.cursor()
    cursor.execute('SELECT id, url, collected_at FROM Links ORDER BY id DESC LIMIT ?', (limit,))
    rows = cursor.fetchall()
    conn.close()
    
    print(f"\n📋 Последние добавленные ссылки:")
    for row in rows:
        print(f"   {row[0]}. {row[1]} (добавлено: {row[2]})")

if __name__ == "__main__":
    # 🔥 ЗАПУСК СБОРА ССЫЛОК
    collect_links()
    
    # Показываем статистику
    total = get_total_links_count()
    print(f"\n📊 ВСЕГО ССЫЛОК В БАЗЕ: {total}")
    
    # Показываем примеры
    show_sample_links()