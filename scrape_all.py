import requests
import json
import re
import bs4
import argparse
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})

def fetch_page(url):
    try:
        response = session.get(url, timeout=10)
        response.encoding = 'utf-8'
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
    
    return {
        'name': name.replace('\n', ' ').strip(),
        'price': f"{price} DKK" if price != "Ukendt" else price,
        'condition': condition,
        'age': age,
        'edited_date': edited_date,
        'location': location,
        'category_path': category_path,
        'image': primary_image,
        'url': url,
        'desc_snippet': desc_snippet
    }

def main():
    parser = argparse.ArgumentParser(description="Skrab DBA for et bestemt produkt eller via en URL.")
    parser.add_argument('--query', type=str, help='Søgestrengen på DBA (bruges hvis --url ikke er angivet)')
    parser.add_argument('--url', type=str, help='En direkte DBA søge-URL, fx en kategori-søgning')
    parser.add_argument('--pages', type=int, default=5, help='Maksimalt antal sider der skal skrabes (standard: 5)')
    parser.add_argument('--output', type=str, default='dba_oversigt.md', help='Navn på output Markdown-filen')
    args = parser.parse_args()

    if not args.query and not args.url:
        args.query = 'fender stratocaster'

    if args.url:
        print(f"Henter alle URLs for linket '{args.url}' op til {args.pages} sider...")
    else:
        print(f"Henter alle URLs for '{args.query}' op til {args.pages} sider...")
        
    all_urls = []
    for p in range(1, args.pages + 1):
        urls = get_item_urls(p, query=args.query, base_url=args.url)
        if not urls:
            print(f"Side {p}: Ingen annoncer fundet. Stopper søgningen efter flere sider.")
            break
        print(f"Side {p}: Fandt {len(urls)} annoncer.")
        all_urls.extend(urls)

    all_urls = list(set(all_urls))
    results = []
    
    if not all_urls:
        print("Søgningen resulterede ikke i nogen annoncer.")
        return

    print(f"I alt {len(all_urls)} unikke annoncer skal hentes.")
    print("Begynder at hente annoncerne (dette kan tage et øjeblik)...")
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_url = {executor.submit(process_item, url): url for url in all_urls}
        for i, future in enumerate(as_completed(future_to_url)):
            res = future.result()
            if res:
                results.append(res)
            if (i+1) % 20 == 0 or (i+1) == len(all_urls):
                print(f"Hentet {i+1}/{len(all_urls)} annoncer")

    results.sort(key=lambda x: x['name'])
    
    title = args.url if args.url else args.query.title()
    
    with open(args.output, 'w', encoding='utf-8') as out:
        out.write(f"# DBA Oversigt for: {title}\n\n")
        out.write(f"*Dato for udtræk: Der blev analyseret {len(results)} annoncer på tværs af maksimalt {args.pages} sider.*\n\n")
        out.write("| Navn | Beskrivelse | Kategori | Lokation | Pris | Stand | Årgang | Oprettet | Billede | URL |\n")
        out.write("|---|---|---|---|---|---|---|---|---|---|\n")
        for r in results:
            img_link = f"[Billede]({r['image']})" if r['image'] != 'Intet billede' else "Intet"
            out.write(f"| {r['name']} | {r['desc_snippet']} | {r['category_path']} | {r['location']} | {r['price']} | {r['condition']} | {r['age']} | {r['edited_date']} | {img_link} | [Link]({r['url']}) |\n")

    print(f"Færdig! Resultater gemt i {args.output}")

if __name__ == '__main__':
    main()
