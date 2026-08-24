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
# 🔥 ЦИКЛ ПО СТРАНИЦАМ: 6 – 9 физика пройден, ИТ 1-3, МАТ 1-3, ХИМ 1-3, ПРАВО 1-3, ИСТОРИЯ 1-8
# ═══════════════════════════════════════════════
URLS_TO_PARSE = [
        # Алфавитные страницы энциклопедии (основной источник)
    'https://godsbay.ru/all_b.html',
    'https://godsbay.ru/all_v.html',
    'https://godsbay.ru/all_g.html',
    'https://godsbay.ru/all_d.html',
    'https://godsbay.ru/all_e.html',
    'https://godsbay.ru/all_j.html',
    'https://godsbay.ru/all_z.html',
    'https://godsbay.ru/all_i.html',
    'https://godsbay.ru/all1.html',      # К
    'https://godsbay.ru/all_l.html',
    'https://godsbay.ru/all_m.html',
    'https://godsbay.ru/all_n.html',
    'https://godsbay.ru/all_o.html',
    'https://godsbay.ru/all_p.html',
    'https://godsbay.ru/all_r.html',
    'https://godsbay.ru/all_s.html',
    'https://godsbay.ru/all_t.html',
    'https://godsbay.ru/all2.html',      # У
    'https://godsbay.ru/all_f.html',
    'https://godsbay.ru/all_h.html',
    'https://godsbay.ru/all_zt.html',    # Ц
    'https://godsbay.ru/all_ch.html',
    'https://godsbay.ru/all_sh.html',
    'https://godsbay.ru/all_ye.html',    # Э
    'https://godsbay.ru/all_yu.html',
    'https://godsbay.ru/all_ya.html',

    'https://godsbay.ru/all.html', 
    'https://godsbay.ru/paint/legenda.html', 
    'https://godsbay.ru/civilizations/', 
    'https://godsbay.ru/paint/', 
    'https://godsbay.ru/antique/',
    'https://godsbay.ru/orient/mesopotamia.html', 
    'https://godsbay.ru/egypt/', 
    'https://godsbay.ru/orient/india.html', 
    'https://godsbay.ru/celts/', 
    'https://godsbay.ru/orient/china.html',   
    'https://godsbay.ru/maya/', 
    'https://godsbay.ru/vikings/', 
    'https://godsbay.ru/slavs/', 
    'https://godsbay.ru/orient/japan.html', 
    'https://godsbay.ru/about.html',
    'https://godsbay.ru/civilizations/civilization_egipet.html', 
    'https://godsbay.ru/civilizations/civilization_mesopotamiya.html', 
    'https://godsbay.ru/civilizations/civilization_indiya.html', 
    'https://godsbay.ru/civilizations/ellinskaya_civilization.html', 
    'https://godsbay.ru/orient/japan.html', 
        'https://godsbay.ru/civilizations/rimskaya_civilizaciya.html',
        'https://godsbay.ru/civilizations/varvarsky_mir.html', 
        'https://godsbay.ru/civilizations/vizantiya.html', 
        'https://godsbay.ru/civilizations/civilization_islam.html', 
        'https://godsbay.ru/civilizations/civilization_yaponiya.html', 
    'https://godsbay.ru/civilizations/srednevekovaya_civilizaciya_zapada.html', 
    'https://godsbay.ru/civilizations/istoki_industrialnoy_civilizacii.html',
    'https://godsbay.ru/civilizations/industrialnaya_civilizaciya.html', 
]

def get_links():
    """Возвращает список ссылок для обработки (без дубликатов)."""
    all_links = set()  # 👈 используем множество для уникальности
    
    for url in URLS_TO_PARSE:
        print(f"🔗 Собираю ссылки с: {url}")
        links = extract_links_from_url(url)
        
        if links:
            print(f"   📝 Найдено ссылок: {len(links)}")
            all_links.update(links)  # 👈 добавляем в множество
        else:
            print("   ❌ Ссылок не найдено")
        
        time.sleep(1)
    
    # Превращаем множество обратно в список
    all_links = list(all_links)
    
    print(f"\n✅ ВСЕГО УНИКАЛЬНЫХ ССЫЛОК: {len(all_links)}")
    return all_links


if __name__ == "__main__":
    links = get_links()
    for i, link in enumerate(links, 1):
        print(f"{i:3}. {link}")