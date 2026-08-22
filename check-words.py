import re
import requests
import time
from get_links import get_links

MIN_WORDS = 400  # Порог

def count_russian_words(url):
    """Считает количество русских слов на странице."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, timeout=30, headers=headers)
        response.raise_for_status()
        html = response.text
    except requests.exceptions.RequestException as e:
        return f"❌ Ошибка: {e}", 0

    # Удаляем теги
    text = re.sub(r'<[^>]+>', ' ', html)
    
    # Оставляем только русские буквы, пробелы и дефис
    text = re.sub(r'[^а-яА-ЯёЁ\- ]', ' ', text)
    
    # Разбиваем на слова
    raw_words = text.split()
    words = set()
    
    for w in raw_words:
        w = w.strip('-')
        if re.fullmatch(r'[а-яА-ЯёЁ\-]+', w):
            if len(w) > 1 and len(w) <= 30:
                words.add(w.lower())
    
    return None, len(words)


def main():
    print("🔗 Получаю список ссылок...")
    URLS = get_links()
    
    if not URLS:
        print("❌ Нет ссылок для обработки.")
        return
    
    print(f"\n📊 Проверяю {len(URLS)} ссылок...\n")
    print("=" * 80)
    print(f"{'Слов':<6} | {'Статус':<10} | Ссылка")
    print("=" * 80)
    
    low_count_links = []
    
    for i, url in enumerate(URLS, 1):
        print(f"\r🔄 [{i}/{len(URLS)}] Обработка...", end="")
        
        error, count = count_russian_words(url)
        
        if error:
            print(f"\n{'':<6} | {'❌ Ошибка':<10} | {url}")
            continue
        
        # Если слов меньше порога — запоминаем
        if count < MIN_WORDS:
            low_count_links.append((url, count))
            print(f"\n{count:<6} | {'⏭️ МАЛО':<10} | {url}")
        else:
            # Для отладки можно раскомментировать:
            # print(f"\n{count:<6} | {'✅ ОК':<10} | {url}")
            pass
        
        # Пауза, чтобы не перегружать сервер
        if i < len(URLS):
            time.sleep(0.5)
    
    print("\n" + "=" * 80)
    print(f"\n📋 НАЙДЕНО СТРАНИЦ С МЕНЕЕ {MIN_WORDS} СЛОВ: {len(low_count_links)}")
    
    if low_count_links:
        print("\n🔽 СПИСОК ДЛЯ ЧЁРНОГО СПИСКА:")
        print("-" * 80)
        for url, count in low_count_links:
            print(f"  {count:>4} слов — {url}")
        
        # Вывод в формате для копирования в чёрный список
        print("\n📋 ДЛЯ КОПИРОВАНИЯ В BLACKLIST:")
        print("-" * 80)
        for url, count in sorted(low_count_links, key=lambda x: x[1]):
            # Извлекаем путь для чёрного списка
            import urllib.parse
            parsed = urllib.parse.urlparse(url)
            path = parsed.path
            # Добавляем слеш в конце, если его нет
            if not path.endswith('/'):
                path += '/'
            print(f"    '/{path.lstrip('/')}',  # {count} слов")
    else:
        print("✅ Все страницы содержат достаточно слов.")


if __name__ == "__main__":
    main()