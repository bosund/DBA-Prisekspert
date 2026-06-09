"""
DISCLAIMER:
Dette program er udelukkende udviklet til uddannelsesmæssige (educational) formål 
og som et personligt projekt. Det er op til brugeren af programmet at overholde gældende 
lovgivning samt handelsbetingelser (Terms of Service) for de hjemmesider, der interageres med. 
Forfatteren tager intet ansvar for misbrug eller blokeringer forårsaget af dette værktøj.
"""

import requests
import json
import re
import bs4
import argparse
import urllib.parse
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:
    import requests_cache
    # Gemmer cachet i en sqlite fil 'dba_cache' og beholder det i 1 time (3600 sekunder)
    requests_cache.install_cache('dba_cache', expire_after=3600)
    CACHE_ENABLED = True
except ImportError:
    CACHE_ENABLED = False

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})

# Konfigurer Retries (prøv op til 3 gange ved netværksfejl, f.eks. ved 'Too Many Requests' 429)
retries = Retry(total=3, backoff_factor=1, status_forcelist=[ 429, 500, 502, 503, 504 ])
adapter = HTTPAdapter(max_retries=retries)
session.mount('http://', adapter)
session.mount('https://', adapter)

def fetch_page(url):
    try:
        response = session.get(url, timeout=10)
        response.encoding = 'utf-8'
        
        # Rate limiting: Hvis svaret er hentet direkte fra nettet (og ikke via cache), tager vi en lille pause
        if not getattr(response, 'from_cache', False):
            time.sleep(random.uniform(0.5, 1.5))
            
        return response.text
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return ""

def get_item_urls(page_num, query=None, base_url=None):
    if base_url:
        parsed_url = urllib.parse.urlparse(base_url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        query_params['page'] = [str(page_num)]
        new_query = urllib.parse.urlencode(query_params, doseq=True)
        url = urllib.parse.urlunparse(parsed_url._replace(query=new_query))
    else:
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://www.dba.dk/recommerce/forsale/search?page={page_num}&q={encoded_query}"
        
    html = fetch_page(url)
    match = re.search(r'<script type="application/ld\+json" id="seoStructuredData">(.*?)</script>', html)
    urls = []
    if match:
        try:
            data = json.loads(match.group(1))
            items = data.get('mainEntity', {}).get('itemListElement', [])
            for item in items:
                product = item.get('item', {})
                if product.get('url'):
                    urls.append(product.get('url'))
        except:
            pass
    return urls

def safe_get(d, keys, default=""):
    for k in keys:
        if isinstance(d, dict) and k in d:
            d = d[k]
        else:
            return default
    return d

def process_item(url):
    html = fetch_page(url)
    if not html:
        return None
        
    name = "Ukendt"
    price = "Ukendt"
    condition = "Ukendt"
    desc = ""
    
    soup = bs4.BeautifulSoup(html, 'html.parser')
    
    scripts = soup.find_all('script', type='application/ld+json')
    for s in scripts:
        if s.string and 'description' in s.string:
            try:
                data = json.loads(s.string)
                if data.get('@type') == 'Product':
                    name = data.get('name', name)
                    price = data.get('offers', {}).get('price', price)
                    cond = data.get('itemCondition', '')
                    if 'UsedCondition' in cond:
                        condition = 'Brugt'
                    elif 'NewCondition' in cond:
                        condition = 'Ny'
            except: pass

    edited_date = "Ikke angivet"
    location = "Ukendt"
    primary_image = "Intet billede"
    category_path = "Ukendt"
    extras_dict = {}

    match_hyd = re.search(r'window\.__staticRouterHydrationData = JSON\.parse\("(.*?)"\);', html)
    if match_hyd:
        raw_str = match_hyd.group(1)
        try:
            data_str = json.loads('"' + raw_str + '"')
            data_dict = json.loads(data_str)
            
            # Extract structured data
            item_recom = safe_get(data_dict, ['loaderData', 'item-recommerce'])
            item_data = safe_get(item_recom, ['itemData'])
            
            # Location
            zipcode = safe_get(item_data, ['location', 'postalCode'])
            city = safe_get(item_data, ['location', 'postalName'])
            if zipcode and city:
                location = f"{zipcode} {city}"
            elif city:
                location = city
                
            # Image
            images = safe_get(item_data, ['images'])
            if isinstance(images, list) and len(images) > 0:
                uri = safe_get(images[0], ['uri'])
                if uri:
                    primary_image = uri
                    
            # Extras (betegnelser/specifikationer)
            item_extras = safe_get(item_data, ['extras'])
            if isinstance(item_extras, list):
                for ext in item_extras:
                    label = ext.get('label')
                    val = ext.get('value')
                    if label and val:
                        extras_dict[label] = val
                    
            # Category
            json_ld = safe_get(item_recom, ['jsonLd'])
            add_props = safe_get(json_ld, ['additionalProperty'])
            if isinstance(add_props, list):
                for prop in add_props:
                    if isinstance(prop, dict) and prop.get('name') == 'category':
                        category_path = prop.get('value', "Ukendt")
            
            def find_desc(d):
                nonlocal desc, edited_date
                if isinstance(d, dict):
                    if 'description' in d and isinstance(d['description'], str) and len(d['description']) > max(len(desc), 20):
                        desc = d['description']
                    for k, v in d.items():
                        if isinstance(v, str) and re.match(r'20\d\d-\d\d-\d\dT', v):
                            if 'edited' in k.lower() or 'created' in k.lower() or 'date' in k.lower():
                                edited_date = v.split('T')[0]
                    for v in d.values():
                        find_desc(v)
                elif isinstance(d, list):
                    for v in d:
                        find_desc(v)
            find_desc(data_dict)
        except Exception:
            pass
            
    if not desc:
        desc_div = soup.find('div', class_='description-area')
        if desc_div:
            desc = desc_div.get_text(separator=' ').strip()
    
    if not name or name == "Ukendt":
        h1_match = soup.find('h1')
        if h1_match: name = h1_match.text.strip()
        
    year_match = re.search(r'\b(19\d{2}|20\d{2})\b', name + " " + desc)
    age = year_match.group(1) if year_match else "Ikke angivet"
    
    desc_snippet = (re.sub(r'\s+', ' ', desc)[:150].strip() + '...') if desc else 'Ingen beskrivelse fundet'
    
    numeric_price = None
    try:
        if isinstance(price, (int, float)):
            numeric_price = int(price)
        elif isinstance(price, str) and price != "Ukendt":
            clean_price = price.replace('.', '').replace(',', '')
            if clean_price.isdigit():
                numeric_price = int(clean_price)
    except:
        pass
        
    final_price = numeric_price if numeric_price is not None else price
    
    return {
        'name': name.replace('\n', ' ').strip(),
        'price': final_price,
        'condition': condition,
        'age': age,
        'edited_date': edited_date,
        'location': location,
        'category_path': category_path,
        'image': primary_image,
        'url': url,
        'desc_snippet': desc_snippet,
        'extras': extras_dict
    }

def get_all_ads(query, url, pages, log_func=print, stop_event=None):
    if url:
        log_func(f"Henter alle URLs for linket '{url}' op til {pages} sider...")
    else:
        log_func(f"Henter alle URLs for '{query}' op til {pages} sider...")
        
    all_urls = []
    for p in range(1, pages + 1):
        if stop_event and stop_event.is_set():
            log_func("Søgning afbrudt af brugeren (ved sidetal).")
            break
            
        urls = get_item_urls(p, query=query, base_url=url)
        if not urls:
            log_func(f"Side {p}: Ingen annoncer fundet. Stopper søgningen efter flere sider.")
            break
        log_func(f"Side {p}: Fandt {len(urls)} annoncer.")
        all_urls.extend(urls)

    if stop_event and stop_event.is_set():
        log_func("Afbrudt før annonce-hentning begyndte.")
        return []

    all_urls = list(set(all_urls))
    results = []
    
    if not all_urls:
        log_func("Søgningen resulterede ikke i nogen annoncer.")
        return []

    log_func(f"I alt {len(all_urls)} unikke annoncer skal hentes.")
    log_func("Begynder at hente annoncerne (dette kan tage et øjeblik)...")
    
    # Skruet ned til max_workers=3 for at være mere skånsom over for DBAs servere
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_url = {executor.submit(process_item, u): u for u in all_urls}
        for i, future in enumerate(as_completed(future_to_url)):
            if stop_event and stop_event.is_set():
                log_func("Hentning af annoncer afbrudt af brugeren. Annullerer resterende forespørgsler...")
                for f in future_to_url:
                    f.cancel()
                break
                
            res = future.result()
            if res:
                results.append(res)
            if (i+1) % 20 == 0 or (i+1) == len(all_urls):
                log_func(f"Hentet {i+1}/{len(all_urls)} annoncer")

    results.sort(key=lambda x: x['name'])
    return results

def write_markdown(results, output_file, title, pages):
    categories = sorted(list(set(r['category_path'] for r in results)))

    with open(output_file, 'w', encoding='utf-8') as out:
        out.write(f"# DBA Oversigt for: {title}\n\n")
        out.write(f"*Dato for udtræk: Der blev analyseret {len(results)} annoncer på tværs af maksimalt {pages} sider.*\n\n")
        
        for idx, cat in enumerate(categories):
            cat_results = [r for r in results if r['category_path'] == cat]
            
            extra_keys = set()
            for r in cat_results:
                extra_keys.update(r.get('extras', {}).keys())
                
            extra_keys = sorted(list(extra_keys))
            if 'Stand' in extra_keys:
                extra_keys.remove('Stand')
                
            out.write(f"## Kategori: {cat}\n\n")
            
            headers = ["Navn", "Beskrivelse", "Lokation", "Pris", "Stand", "Årgang"] + extra_keys + ["Oprettet", "Billede", "URL"]
            out.write("| " + " | ".join(headers) + " |\n")
            out.write("|" + "|".join(["---"] * len(headers)) + "|\n")
            
            for r in cat_results:
                img_link = f"[Billede]({r['image']})" if r['image'] != 'Intet billede' else "Intet"
                price_str = f"{r['price']} DKK" if isinstance(r['price'], int) else str(r['price'])
                
                row = [
                    r['name'], r['desc_snippet'], r['location'],
                    price_str, r['condition'], r['age']
                ]
                for k in extra_keys:
                    row.append(str(r.get('extras', {}).get(k, '')))
                row.extend([r['edited_date'], img_link, f"[Link]({r['url']})"])
                
                out.write("| " + " | ".join(row) + " |\n")
                
            if idx < len(categories) - 1:
                # 2 linjers afstand (Markdown kræver enten <br> eller blot flere blanke linjer. Vi bruger 3 blanke linjer)
                out.write("\n\n\n")

def write_excel(results, output_file, title, pages):
    import pandas as pd
    categories = sorted(list(set(r['category_path'] for r in results)))
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        start_row = 0
        for idx, cat in enumerate(categories):
            cat_results = [r for r in results if r['category_path'] == cat]
            
            extra_keys = set()
            for r in cat_results:
                extra_keys.update(r.get('extras', {}).keys())
                
            extra_keys = sorted(list(extra_keys))
            if 'Stand' in extra_keys:
                extra_keys.remove('Stand')
                
            flattened = []
            for r in cat_results:
                flat_r = r.copy()
                for k in extra_keys:
                    flat_r[k] = flat_r.get('extras', {}).get(k, '')
                if 'extras' in flat_r:
                    del flat_r['extras']
                flattened.append(flat_r)
                
            df = pd.DataFrame(flattened)
            
            base_cols = ['name', 'desc_snippet', 'location', 'price', 'condition', 'age']
            end_cols = ['edited_date', 'image', 'url']
            
            final_cols = []
            for c in base_cols:
                if c in df.columns: final_cols.append(c)
            for c in extra_keys:
                if c in df.columns: final_cols.append(c)
            for c in end_cols:
                if c in df.columns: final_cols.append(c)
                
            df = df[final_cols]
            
            df.rename(columns={
                'name': 'Navn', 'price': 'Pris (DKK)', 'condition': 'Stand', 
                'age': 'Årgang', 'edited_date': 'Dato', 'location': 'Lokation', 
                'image': 'Billede', 'url': 'Link', 'desc_snippet': 'Beskrivelse'
            }, inplace=True)
            
            # Skriv kategoriens navn før selve tabellen
            title_df = pd.DataFrame([[f"Kategori: {cat}"]])
            title_df.to_excel(writer, startrow=start_row, index=False, header=False)
            start_row += 1
            
            # Skriv DataFrame
            df.to_excel(writer, startrow=start_row, index=False)
            
            # start_row opdateres. len(df) er antal datarækker, +1 for kolonneoverskrifter, +2 for at få 2 tomme rækker bagefter
            start_row += len(df) + 1 + 2

def main():
    parser = argparse.ArgumentParser(description="Skrab DBA for et bestemt produkt eller via en URL.")
    parser.add_argument('--query', type=str, help='Søgestrengen på DBA (bruges hvis --url ikke er angivet)')
    parser.add_argument('--url', type=str, help='En direkte DBA søge-URL, fx en kategori-søgning')
    parser.add_argument('--pages', type=int, default=5, help='Maksimalt antal sider der skal skrabes (standard: 5)')
    parser.add_argument('--output', type=str, default='dba_oversigt.md', help='Navn på output Markdown-filen')
    args = parser.parse_args()

    if not args.query and not args.url:
        args.query = 'fender stratocaster'

    results = get_all_ads(args.query, args.url, args.pages, print)
    
    if results:
        title = args.url if args.url else args.query.title()
        write_markdown(results, args.output, title, args.pages)
        print(f"Færdig! Resultater gemt i {args.output}")

if __name__ == '__main__':
    main()
