import re
import sqlite3
import requests
import time
import socket
from get_links import get_links

MIN_WORDS = 150
LOG_FILE = 'inserted_words.log'

def wait_for_internet(host='8.8.8.8', port=53, timeout=3):
    """Проверяет доступность интернета и ждёт, пока он появится."""
    while True:
        try:
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            return True
        except socket.error:
            print("🌐 Нет интернета. Жду 15 секунд...")
            time.sleep(15)

def log_word(word):
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{word}\n")
    except Exception as e:
        print(f"⚠️ Ошибка записи в лог: {e}")

def extract_russian_words_from_url(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, timeout=30, headers=headers)
        response.raise_for_status()
        html = response.text
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка загрузки страницы {url}: {e}")
        return []

    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'[^а-яА-ЯёЁ\- ]', ' ', text)
    raw_words = text.split()
    words = set()
    
    for w in raw_words:
        w = w.strip('-')
        if re.fullmatch(r'[а-яА-ЯёЁ\-]+', w):
            if len(w) > 1 and len(w) <= 30:
                words.add(w.lower())
    
    return sorted(words)

def save_words_to_db(words, db_path='words.db', max_retries=5):
    if len(words) < MIN_WORDS:
        print(f"   ⏭️ Пропущено: всего {len(words)} слов (меньше {MIN_WORDS})")
        return
    
    for attempt in range(max_retries):
        try:
            conn = sqlite3.connect(db_path, timeout=10)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    value TEXT UNIQUE NOT NULL
                )
            ''')
            conn.commit()
            
            inserted = 0
            skipped = 0
            
            for word in words:
                try:
                    cursor.execute('INSERT OR IGNORE INTO Words (value) VALUES (?)', (word,))
                    conn.commit()
                    
                    if cursor.rowcount > 0:
                        inserted += 1
                        print(f"✅ Записано: {word}")
                        log_word(word)
                    else:
                        skipped += 1
                        
                except sqlite3.OperationalError as e:
                    if 'locked' in str(e):
                        print(f"⚠️ База заблокирована, попытка {attempt+1}/{max_retries}...")
                        conn.close()
                        time.sleep(2)
                        break
                    else:
                        print(f"⚠️ Ошибка: {e}")
            
            conn.close()
            print(f"   ➡️ Вставлено: {inserted}, пропущено: {skipped}")
            return True
            
        except sqlite3.OperationalError as e:
            if 'locked' in str(e) and attempt < max_retries - 1:
                print(f"⚠️ База заблокирована, повторная попытка {attempt+2}/{max_retries}...")
                time.sleep(2)
                continue
            else:
                print(f"❌ Ошибка: {e}")
                return False
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False
    
    return False

def main():
    URLS = get_links()
    
    if not URLS:
        print("❌ Нет ссылок для обработки. Проверьте get_links.py")
        return
    
    total_words = set()
    
    for i, url in enumerate(URLS, 1):
        # 🔥 Ждём интернет перед каждой загрузкой
        wait_for_internet()
        
        print(f"\n🌐 [{i}/{len(URLS)}] Загружаю: {url}")
        words = extract_russian_words_from_url(url)
        
        if words:
            print(f"   📝 Найдено {len(words)} слов")
            save_words_to_db(words)
            total_words.update(words)
        else:
            print("   ❌ Не удалось извлечь слова.")
        
        if i < len(URLS):
            time.sleep(15)
    
    print(f"\n🎯 ВСЕГО УНИКАЛЬНЫХ СЛОВ СО ВСЕХ СТРАНИЦ: {len(total_words)}")

if __name__ == "__main__":
    main()