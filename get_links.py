import requests
from urllib.parse import urljoin, urlparse
import re
from blacklist import BLACKLIST  # 👈 Импортируем чёрный список
import time

def is_blacklisted(url):
    """Проверяет, содержит ли URL путь из чёрного списка для этого домена."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    
    # Убираем www. если есть
    if domain.startswith('www.'):
        domain = domain[4:]
    
    path = parsed.path.lower().rstrip('/')
    
    # Если для этого домена есть чёрный список
    if domain in BLACKLIST:
        for blocked in BLACKLIST[domain]:
            blocked_clean = blocked.rstrip('/')
            if blocked_clean in path:
                return True
    
    return False

def extract_links_from_url(url, base_url=None):
    """
    Извлекает все ссылки со страницы.
    Возвращает список абсолютных URL (без мусора).
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

    # Ищем все теги <a href="...">
    pattern = re.compile(r'href\s*=\s*["\']?([^"\'\s>]+)["\']?', re.IGNORECASE)
    raw_links = pattern.findall(html)
    
    # Расширения, которые нужно исключить
    SKIP_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.webp',
                       '.json', '.xml', '.css', '.js', '.pdf', '.zip', '.rar',
                       '.mp4', '.mp3', '.avi', '.mkv', '.exe', '.dmg' , '.woff' , '.woff2')
    
    absolute_links = []
    seen = set()
    parsed_base = urlparse(base_url)
    
    for raw_link in raw_links:
        if not raw_link or raw_link.startswith('#') or raw_link.startswith('javascript:'):
            continue
            
        full_url = urljoin(base_url, raw_link)
        
        if '#' in full_url:
            full_url = full_url.split('#')[0]
        
        # 1. Пропускаем расширения файлов
        if full_url.lower().endswith(SKIP_EXTENSIONS):
            continue
        
        # 2. Проверяем чёрный список
        if is_blacklisted(full_url):
            continue
        
        # 3. Оставляем только ссылки на тот же домен
        parsed_full = urlparse(full_url)
        if parsed_base.netloc == parsed_full.netloc and full_url not in seen:
            seen.add(full_url)
            absolute_links.append(full_url)
    
    return absolute_links


# ═══════════════════════════════════════════════
# 🔥 ЦИКЛ ПО СТРАНИЦАМ: 6 – 9 (1 - 9) физика пройден, ИТ 59 (1 - 60), МАТ 1-3, ХИМ 1-3, ПРАВО 1-3, ИСТОРИЯ 1-8
# ═══════════════════════════════════════════════
URLS_TO_PARSE = [
    'https://azbyka.ru/otechnik/'
    #f'https://cyberleninka.ru/article/c/computer-and-information-sciences/{i}'
    #for i in range(40, 60)
]

def get_links():
    """
    Собирает ссылки с глубиной 2 (начальные страницы + все найденные).
    Без ограничения по количеству страниц.
    """
    all_links = set()
    visited = set()
    queue = list(URLS_TO_PARSE)
    page_count = 0
    
    # Уровни глубины
    current_depth = 1
    next_level_urls = []
    
    print("🚀 Начинаем сбор ссылок (глубина 2)...")
    
    while queue:
        url = queue.pop(0)
        
        if url in visited:
            continue
        
        visited.add(url)
        page_count += 1
        
        print(f"\n🔗 [{page_count}] Собираю ссылки с: {url} (глубина {current_depth})")
        links = extract_links_from_url(url)
        
        if links:
            print(f"   📝 Найдено ссылок: {len(links)}")
            
            new_links = 0
            for link in links:
                if link not in visited:
                    all_links.add(link)
                    new_links += 1
                    # Если мы на глубине 1, добавляем ссылки в очередь для второго уровня
                    if current_depth == 1:
                        next_level_urls.append(link)
            
            print(f"   ➡️ Новых ссылок: {new_links}")
            print(f"   📊 Всего уникальных ссылок собрано: {len(all_links)}")
        else:
            print("   ❌ Ссылок не найдено")
        
        # Если очередь пуста и есть ссылки для следующего уровня
        if not queue and next_level_urls and current_depth == 1:
            print(f"\n📂 Переходим на глубину 2...")
            print(f"   ➡️ Обработано страниц уровня 1: {page_count}")
            print(f"   ➡️ Найдено ссылок для уровня 2: {len(next_level_urls)}")
            queue = list(next_level_urls)
            next_level_urls = []
            current_depth = 2
        
        # Задержка между запросами (чтобы не забанили)
        time.sleep(1)  # Оставляем 1 секунду, как у вас было
    
    all_links = list(all_links)
    print(f"\n✅ ИТОГО ОБРАБОТАНО СТРАНИЦ: {page_count}")
    print(f"✅ ВСЕГО УНИКАЛЬНЫХ ССЫЛОК СОБРАНО: {len(all_links)}")
    return all_links

if __name__ == "__main__":
    links = get_links()
    for i, link in enumerate(links, 1):
        print(f"{i:3}. {link}")