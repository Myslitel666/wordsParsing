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
# 🔥 ЦИКЛ ПО СТРАНИЦАМ: 6 – 9 физика пройден
# ═══════════════════════════════════════════════
PAGE_START = 1
PAGE_END = 3
BASE_URL = "https://cyberleninka.ru/article/c/computer-and-information-sciences"

def get_links():
    """Собирает ссылки со всех страниц в диапазоне."""
    all_links = []
    
    for page in range(PAGE_START, PAGE_END + 1):
        url = f"{BASE_URL}{page}"
        print(f"🔗 Собираю ссылки с: {url}")
        links = extract_links_from_url(url)
        
        if links:
            print(f"   📝 Найдено ссылок: {len(links)}")
            all_links.extend(links)
        else:
            print("   ❌ Ссылок не найдено")
        
        time.sleep(1)
    
    print(f"\n✅ ВСЕГО СОБРАНО ССЫЛОК: {len(all_links)}")
    return all_links


if __name__ == "__main__":
    links = get_links()
    for i, link in enumerate(links, 1):
        print(f"{i:3}. {link}")