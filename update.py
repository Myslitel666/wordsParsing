import re
import sqlite3
import requests
import time
import socket
from get_links import get_links

MIN_WORDS = 50
LOG_FILE = 'updated_words.log'

def wait_for_internet(host='8.8.8.8', port=53, timeout=3):
    """Проверяет доступность интернета и ждёт, пока он появится."""
    while True:
        try:
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            return True
        except socket.error:
            print("🌐 Нет интернета. Жду 15 секунд...")
            time.sleep(8)

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
                if w.isupper() and len(w) == 3:
                    words.add(w)
                elif w.isupper() and len(w) != 3:
                    continue
                else:
                    words.add(w.lower())
    
    return sorted(words)

def update_words_in_db(words, url, db_path='words.db', max_retries=5):
    if len(words) < MIN_WORDS:
        print(f"   ⏭️ Пропущено: всего {len(words)} слов (меньше {MIN_WORDS})")
        return set(), set()
    
    for attempt in range(max_retries):
        try:
            conn = sqlite3.connect(db_path, timeout=10)
            cursor = conn.cursor()
            
            # Проверяем, существует ли поле link в таблице Words
            cursor.execute("PRAGMA table_info(Words)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'link' not in columns:
                print("   📝 Добавляем поле link в таблицу Words...")
                cursor.execute('ALTER TABLE Words ADD COLUMN link TEXT')
                conn.commit()
                print("   ✅ Поле link добавлено!")
            
            updated_words = set()
            not_found_words = set()
            
            for word in words:
                try:
                    # Проверяем, есть ли слово в базе и link пустой
                    cursor.execute('SELECT link FROM Words WHERE value = ? AND link IS NULL', (word,))
                    result = cursor.fetchone()
                    
                    if result:
                        # Обновляем только если link пустой
                        cursor.execute('UPDATE Words SET link = ? WHERE value = ? AND link IS NULL', (url, word))
                        conn.commit()
                        
                        if cursor.rowcount > 0:
                            updated_words.add(word)
                            print(f"✅ Обновлено: {word}")
                            log_word(word)
                    else:
                        # Проверяем, существует ли слово вообще
                        cursor.execute('SELECT value FROM Words WHERE value = ?', (word,))
                        exists = cursor.fetchone()
                        if not exists:
                            not_found_words.add(word)
                        
                except sqlite3.OperationalError as e:
                    if 'locked' in str(e):
                        print(f"⚠️ База заблокирована, попытка {attempt+1}/{max_retries}...")
                        conn.close()
                        time.sleep(2)
                        break
                    else:
                        print(f"⚠️ Ошибка: {e}")
            
            conn.close()
            print(f"   ➡️ Найдено слов на странице: {len(words)}, обновлено: {len(updated_words)}, не найдено: {len(not_found_words)}")
            return updated_words, not_found_words
            
        except sqlite3.OperationalError as e:
            if 'locked' in str(e) and attempt < max_retries - 1:
                print(f"⚠️ База заблокирована, повторная попытка {attempt+2}/{max_retries}...")
                time.sleep(2)
                continue
            else:
                print(f"❌ Ошибка: {e}")
                return set(), set()
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return set(), set()
    
    return set(), set()

def main():
    URLS = get_links()
    
    if not URLS:
        print("❌ Нет ссылок для обработки. Проверьте get_links.py")
        return
    
    all_words = set()
    all_updated_words = set()
    all_not_found_words = set()
    
    for i, url in enumerate(URLS, 1):
        wait_for_internet()
        
        print(f"\n🌐 [{i}/{len(URLS)}] Загружаю: {url}")
        words = extract_russian_words_from_url(url)
        
        if words:
            print(f"   📝 Найдено {len(words)} слов")
            updated_words, not_found_words = update_words_in_db(words, url)
            all_words.update(words)
            all_updated_words.update(updated_words)
            all_not_found_words.update(not_found_words)
        else:
            print("   ❌ Не удалось извлечь слова.")
        
        if i < len(URLS):
            time.sleep(1)
    
    print(f"\n🎯 ВСЕГО УНИКАЛЬНЫХ СЛОВ СО ВСЕХ СТРАНИЦ: {len(all_words)}")
    print(f"📊 ВСЕГО УНИКАЛЬНЫХ ОБНОВЛЕННЫХ СЛОВ: {len(all_updated_words)}")
    print(f"📊 ВСЕГО УНИКАЛЬНЫХ НЕ НАЙДЕННЫХ СЛОВ: {len(all_not_found_words)}")

if __name__ == "__main__":
    main()