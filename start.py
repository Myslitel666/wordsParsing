import re
import sqlite3
import requests
import time
from get_links import get_links

def extract_russian_words_from_url(url):
    """Извлекает только русские слова из HTML-страницы."""
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

    # Удаляем теги
    text = re.sub(r'<[^>]+>', ' ', html)
    
    # Оставляем только русские буквы, пробелы и дефис
    text = re.sub(r'[^а-яА-ЯёЁ\- ]', ' ', text)
    
    # Разбиваем на слова
    raw_words = text.split()
    words = set()
    
    for w in raw_words:
        w = w.strip('-')
        # Проверяем, что слово состоит только из русских букв (и дефиса внутри)
        if re.fullmatch(r'[а-яА-ЯёЁ\-]+', w):
            if len(w) > 1 and len(w) <= 30:
                words.add(w.lower())
    
    return sorted(words)

def save_words_to_db(words, db_path='words.db'):
    """Сохраняет слова в базу SQLite."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                value TEXT UNIQUE NOT NULL
            )
        ''')
        conn.commit()
        
    except sqlite3.Error as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        return
    
    total = len(words)
    inserted = 0
    skipped = 0
    
    for word in words:
        try:
            cursor.execute('INSERT OR IGNORE INTO Words (value) VALUES (?)', (word,))
            conn.commit()
            
            if cursor.rowcount > 0:
                inserted += 1
                print(f"✅ Записано: {word}")
            else:
                skipped += 1
                
        except sqlite3.Error as e:
            print(f"⚠️ Ошибка при вставке слова '{word}': {e}")
    
    conn.close()
    print(f"   ➡️ Вставлено: {inserted}, пропущено: {skipped}")

def main():
    # Получаем ссылки из get_links.py
    URLS = get_links()
    
    if not URLS:
        print("❌ Нет ссылок для обработки. Проверьте get_links.py")
        return
    
    total_words = set()
    
    for i, url in enumerate(URLS, 1):
        print(f"\n🌐 [{i}/{len(URLS)}] Загружаю: {url}")
        words = extract_russian_words_from_url(url)
        
        if words:
            print(f"   📝 Найдено {len(words)} слов")
            save_words_to_db(words)
            total_words.update(words)
        else:
            print("   ❌ Не удалось извлечь слова.")
        
        # Пауза между запросами
        if i < len(URLS):
            time.sleep(1)
    
    print(f"\n🎯 ВСЕГО УНИКАЛЬНЫХ СЛОВ СО ВСЕХ СТРАНИЦ: {len(total_words)}")

if __name__ == "__main__":
    main()