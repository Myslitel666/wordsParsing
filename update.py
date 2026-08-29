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
        return 0, 0
    
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
            
            updated = 0
            not_found = 0
            
            for word in words:
                try:
                    # Проверяем, есть ли слово в базе
                    cursor.execute('SELECT link FROM Words WHERE value = ?', (word,))
                    result = cursor.fetchone()
                    
                    if result:
                        current_link = result[0]
                        
                        # Если ссылка уже есть, добавляем через запятую
                        if current_link:
                            if url not in current_link.split(','):
                                new_link = f"{current_link},{url}"
                            else:
                                new_link = current_link
                        else:
                            new_link = url
                        
                        # Обновляем запись сразу по value
                        cursor.execute('UPDATE Words SET link = ? WHERE value = ?', (new_link, word))
                        conn.commit()
                        
                        if cursor.rowcount > 0:
                            updated += 1
                            print(f"✅ Обновлено: {word}")
                            log_word(word)
                    else:
                        not_found += 1
                        
                except sqlite3.OperationalError as e:
                    if 'locked' in str(e):
                        print(f"⚠️ База заблокирована, попытка {attempt+1}/{max_retries}...")
                        conn.close()
                        time.sleep(2)
                        break
                    else:
                        print(f"⚠️ Ошибка: {e}")
            
            conn.close()
            print(f"   ➡️ Найдено слов на странице: {len(words)}, обновлено: {updated}, не найдено: {not_found}")
            return updated, not_found
            
        except sqlite3.OperationalError as e:
            if 'locked' in str(e) and attempt < max_retries - 1:
                print(f"⚠️ База заблокирована, повторная попытка {attempt+2}/{max_retries}...")
                time.sleep(2)
                continue
            else:
                print(f"❌ Ошибка: {e}")
                return 0, 0
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return 0, 0
    
    return 0, 0

def main():
    URLS = get_links()
    
    if not URLS:
        print("❌ Нет ссылок для обработки. Проверьте get_links.py")
        return
    
    total_words = set()
    total_updated = 0
    total_not_found = 0
    
    for i, url in enumerate(URLS, 1):
        wait_for_internet()
        
        print(f"\n🌐 [{i}/{len(URLS)}] Загружаю: {url}")
        words = extract_russian_words_from_url(url)
        
        if words:
            print(f"   📝 Найдено {len(words)} слов")
            updated, not_found = update_words_in_db(words, url)
            total_updated += updated
            total_not_found += not_found
            total_words.update(words)
        else:
            print("   ❌ Не удалось извлечь слова.")
        
        if i < len(URLS):
            time.sleep(1)
    
    print(f"\n🎯 ВСЕГО УНИКАЛЬНЫХ СЛОВ СО ВСЕХ СТРАНИЦ: {len(total_words)}")
    print(f"📊 ВСЕГО ОБНОВЛЕНО: {total_updated}, НЕ НАЙДЕНО: {total_not_found}")

if __name__ == "__main__":
    main()