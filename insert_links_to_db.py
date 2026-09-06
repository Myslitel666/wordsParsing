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
        # Пропускаем пустые, якоря и javascript
        if not raw_link or raw_link.startswith('#') or raw_link.startswith('javascript:'):
            continue
            
        # Склеиваем относительную ссылку с базовым URL
        full_url = urljoin(base_url, raw_link)
        
        # 🔥 ПРОПУСКАЕМ ЯКОРНЫЕ ССЫЛКИ (содержат только #)
        if '#' in full_url:
            # Обрезаем якорь
            base_without_fragment = full_url.split('#')[0]
            # Если после обрезания якоря остался только базовый URL - пропускаем
            if base_without_fragment == base_url or base_without_fragment == base_url + '/':
                continue
            # Иначе используем URL без якоря
            full_url = base_without_fragment
        
        # Пропускаем файлы с расширениями
        if full_url.lower().endswith(SKIP_EXTENSIONS):
            continue
        
        # Проверяем чёрный список
        if is_blacklisted(full_url):
            continue
        
        # Оставляем только ссылки на тот же домен
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
    """Основная функция сбора ссылок (3 вложенных цикла)."""
    URLS_TO_PARSE = ['https://azbyka.ru/otechnik/']
    
    init_database()
    conn = sqlite3.connect(DB_PATH, timeout=10)
    
    all_links = set()
    page_count = 0
    
    print("🚀 Начинаем сбор ссылок...")
    wait_for_internet()
    
    # ══════════════════════════════════════════
    # 🔥 ШАГ 1: Собираем всех авторов (отёчник → буквы → авторы)
    # ══════════════════════════════════════════
    print("\n📚 ШАГ 1: Собираю авторов...")
    
    authors = []
    queue = list(URLS_TO_PARSE)  # Начинаем с отёчника
    
    while queue:
        url = queue.pop(0)
        
        cursor = conn.cursor()
        cursor.execute('SELECT processed FROM Links WHERE url = ?', (url,))
        row = cursor.fetchone()
        
        if row is not None and row[0] == 1:
            print(f"⏭️ Пропускаю (уже обработана): {url}")
            continue
        
        page_count += 1
        print(f"\n🔗 [{page_count}] Собираю авторов с: {url}")
        
        wait_for_internet()
        links = extract_links_from_url(url)
        
        if links:
            print(f"   📝 Найдено ссылок: {len(links)}")
            
            new_links = []
            for link in links:
                cursor = conn.cursor()
                cursor.execute('SELECT 1 FROM Links WHERE url = ?', (link,))
                if cursor.fetchone() is None:
                    new_links.append(link)
                    all_links.add(link)
                    
                    # Если это страница автора — запоминаем для вложенного цикла
                    if '/otechnik/' in link and link.count('/') == 4:
                        authors.append(link)
                    else:
                        queue.append(link)  # Промежуточные страницы (буквы)
            
            print(f"   ➡️ Новых ссылок: {len(new_links)}")
            print(f"   📊 Всего уникальных ссылок собрано: {len(all_links)}")
            print(f"   📊 Найдено авторов: {len(authors)}")
            
            if new_links:
                save_links_to_db(conn, new_links)
        else:
            print("   ❌ Ссылок не найдено")
        
        time.sleep(DELAY_BETWEEN_REQUESTS)
    
    # ══════════════════════════════════════════
    # 🔥 ШАГ 2: ВЛОЖЕННЫЙ ЦИКЛ ПО АВТОРАМ → КНИГАМ → ГЛАВАМ
    # ══════════════════════════════════════════
    print(f"\n📚 ШАГ 2: Обрабатываю {len(authors)} авторов...")
    
    for author_url in authors:
        print(f"\n📖 Обрабатываю автора: {author_url}")
        
        # Проверяем, обработан ли уже автор
        cursor = conn.cursor()
        cursor.execute('SELECT processed FROM Links WHERE url = ?', (author_url,))
        row = cursor.fetchone()
        
        if row is not None and row[0] == 1:
            print(f"⏭️ Пропускаю (уже обработан): {author_url}")
            continue
        
        # ══════════════════════════════════════
        # 🔥 ЦИКЛ 1: КНИГИ АВТОРА
        # ══════════════════════════════════════
        print(f"   📚 Собираю книги автора {author_url}...")
        
        books = []
        page_count += 1
        
        wait_for_internet()
        links = extract_links_from_url(author_url)
        
        if links:
            print(f"   📝 Найдено ссылок: {len(links)}")
            
            new_links = []
            for link in links:
                cursor = conn.cursor()
                cursor.execute('SELECT 1 FROM Links WHERE url = ?', (link,))
                if cursor.fetchone() is None:
                    new_links.append(link)
                    all_links.add(link)
                    
                    # Если это страница книги — запоминаем для вложенного цикла
                    if '/otechnik/' in link and link.count('/') == 5:
                        books.append(link)
            
            print(f"   ➡️ Новых ссылок: {len(new_links)}")
            print(f"   📊 Всего уникальных ссылок собрано: {len(all_links)}")
            print(f"   📊 Найдено книг: {len(books)}")
            
            if new_links:
                save_links_to_db(conn, new_links)
        else:
            print("   ❌ Ссылок не найдено")
        
        # ══════════════════════════════════════
        # 🔥 ЦИКЛ 2: ГЛАВЫ КНИГ
        # ══════════════════════════════════════
        for book_url in books:
            print(f"\n   📖 Обрабатываю книгу: {book_url}")
            
            # Проверяем, обработана ли уже книга
            cursor = conn.cursor()
            cursor.execute('SELECT processed FROM Links WHERE url = ?', (book_url,))
            row = cursor.fetchone()
            
            if row is not None and row[0] == 1:
                print(f"   ⏭️ Пропускаю (уже обработана): {book_url}")
                continue
            
            page_count += 1
            
            wait_for_internet()
            links = extract_links_from_url(book_url)
            
            if links:
                print(f"   📝 Найдено ссылок: {len(links)}")
                
                new_links = []
                for link in links:
                    cursor = conn.cursor()
                    cursor.execute('SELECT 1 FROM Links WHERE url = ?', (link,))
                    if cursor.fetchone() is None:
                        new_links.append(link)
                        all_links.add(link)
                        # Это главы — добавляем в базу, но не запоминаем
                
                print(f"   ➡️ Новых ссылок: {len(new_links)}")
                print(f"   📊 Всего уникальных ссылок собрано: {len(all_links)}")
                
                if new_links:
                    save_links_to_db(conn, new_links)
            else:
                print("   ❌ Ссылок не найдено")
            
            # ✅ Книга обработана → ставим processed=1
            mark_as_processed(conn, book_url)
            print(f"   ✅ Книга помечена как обработанная (processed=1)")
            
            time.sleep(DELAY_BETWEEN_REQUESTS)
        
        # ✅ Автор обработан → ставим processed=1
        mark_as_processed(conn, author_url)
        print(f"   ✅ Автор помечен как обработанный (processed=1)")
        
        time.sleep(DELAY_BETWEEN_REQUESTS)
    
    # ══════════════════════════════════════════
    # 🔥 ФИНАЛ: отёчник
    # ══════════════════════════════════════════
    print(f"\n🏁 СКРИПТ ЗАВЕРШЁН! Помечаю отёчник как обработанный...")
    mark_as_processed(conn, 'https://azbyka.ru/otechnik/')
    print(f"   ✅ Отёчник помечен как обработанный (processed=1)")
    
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