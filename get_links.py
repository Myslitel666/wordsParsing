import requests
from urllib.parse import urljoin, urlparse
import sys

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

    # Если базовый URL не указан, берём из текущей страницы
    if base_url is None:
        base_url = url

    # Ищем все теги <a href="...">
    import re
    # Упрощённый поиск: ищем href="..." или href='...'
    pattern = re.compile(r'href\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
    raw_links = pattern.findall(html)
    
    absolute_links = []
    seen = set()
    
    for raw_link in raw_links:
        # Пропускаем якоря (#глава) и пустые ссылки
        if not raw_link or raw_link.startswith('#') or raw_link.startswith('javascript:'):
            continue
            
        # Превращаем относительную ссылку в абсолютную
        full_url = urljoin(base_url, raw_link)
        
        # Убираем якоря внутри URL (всё после #)
        if '#' in full_url:
            full_url = full_url.split('#')[0]
        
        # Проверяем, что ссылка ведёт на тот же домен (опционально)
        # Можно убрать это условие, если нужны все ссылки
        if full_url.startswith('http') and full_url not in seen:
            seen.add(full_url)
            absolute_links.append(full_url)
    
    return absolute_links


# ═══════════════════════════════════════════════
# 🔥 ЗДЕСЬ ССЫЛКА ДЛЯ ТЕСТА
# ═══════════════════════════════════════════════
URL = "https://azbyka.ru/otechnik/Lazar_Abashidze/greh-i-pokajanie-poslednih-vremen/"
# ═══════════════════════════════════════════════

def main():
    print(f"🌐 Загружаю: {URL}")
    links = extract_links_from_url(URL)
    
    if links:
        print(f"\n📝 Найдено ссылок: {len(links)}")
        for i, link in enumerate(links, 1):
            print(f"{i:3}. {link}")
    else:
        print("❌ Ссылок не найдено или ошибка загрузки.")

if __name__ == "__main__":
    main()