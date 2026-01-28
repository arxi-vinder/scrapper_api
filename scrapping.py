import asyncio
import random
import httpx
from bs4 import BeautifulSoup
import argparse
from urllib.parse import urlencode, quote_plus


ARXIV_FIELDS = {
    # Mathematics
    "math": 100,

    # Statistics
    "stat": 50,

    # Computer Science
    "cs": 100,

    # Physics (umum & spesifik)
    "physics": 50,
    "astro-ph": 40,          # Astrophysics
    "cond-mat": 40,          # Condensed Matter
    "gr-qc": 30,             # General Relativity and Quantum Cosmology
    "hep-ex": 30,            # High Energy Physics - Experiment
    "hep-lat": 30,           # High Energy Physics - Lattice
    "hep-ph": 30,            # High Energy Physics - Phenomenology
    "hep-th": 30,            # High Energy Physics - Theory
    "quant-ph": 30,          # Quantum Physics
    "nucl-ex": 20,           # Nuclear Experiment
    "nucl-th": 20,           # Nuclear Theory

    # Electrical Engineering & Systems Science
    "eess": 40,

    # Economics
    "econ": 30,

    # Quantitative Biology
    "q-bio": 30,

    # Quantitative Finance
    "q-fin": 30
}


def arxiv_pages(fields):
    pages = {}
    for category, total_articles in fields.items():
        category_pages = []
        # Perbaikan URL: Tambahkan /list/ sebelum category
        for skip in range(0, total_articles, 25): # ArXiv default show 25 atau 50
            page = f"https://arxiv.org/list/{category}/pastweek?skip={skip}&show=25"
            category_pages.append(page)
        pages[category] = category_pages
    return pages


def build_advanced_search_url(category='computer_science', from_date=None, to_date=None, size=200, order=''):
    """Builds an arXiv advanced search URL with dynamic classification/category and date range.

    category should be a string like 'computer_science' or 'mathematics'.
    from_date and to_date should be in YYYY-MM or YYYY-MM-DD formats accepted by arXiv.
    """
    base = 'https://arxiv.org/search/advanced'
    params = {
        'advanced': '',
        'terms-0-operator': 'AND',
        'terms-0-term': '',
        'terms-0-field': 'title',
        'classification-physics_archives': 'all',
        'classification-include_cross_list': 'include',
        'date-year': '',
        'date-filter_by': 'date_range' if (from_date or to_date) else '',
        'date-from_date': from_date or '',
        'date-to_date': to_date or '',
        'date-date_type': 'submitted_date',
        'abstracts': 'show',
        'size': str(size),
        'order': order,
    }

    # Enable the chosen classification (e.g., classification-computer_science=y)
    params[f'classification-{category}'] = 'y'

    # urlencode but keep empty values as-is
    query = urlencode(params, doseq=True, quote_via=quote_plus)
    return f"{base}?{query}"


def extract_ids_from_advanced_search(html):
    soup = BeautifulSoup(html, 'html.parser')
    ids = []
    for result in soup.select('li.arxiv-result'):
        a = result.find('p', class_='list-title is-inline-block')
        if a:
            link = a.find('a')
            if link and link.get('href'):
                href = link['href']
                # href like /abs/XXXX.XXXXX
                ids.append(href.split('/')[-1]) # type: ignore
    # fallback: also look for links with title Abstract
    if not ids:
        for a_tag in soup.find_all('a', title='Abstract'):
            href = a_tag.get('href', '')
            if href and isinstance(href, str):
                ids.append(href.split('/')[-1])
    return ids


async def fetch_advanced_search(client, category='computer_science', from_date=None, to_date=None, size=200, order=''):
    url = build_advanced_search_url(category=category, from_date=from_date, to_date=to_date, size=size, order=order)
    print(f"Fetching advanced search URL: {url}")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        resp = await client.get(url, headers=headers, timeout=30.0)
        if resp.status_code == 200:
            ids = extract_ids_from_advanced_search(resp.text)
            print(f"Found {len(ids)} ids on advanced search page")
            return ids
        else:
            print(f"Advanced search failed: {resp.status_code}")
    except Exception as e:
        print(f"Exception fetching advanced search: {e}")
    return []

def extract_id(html):
    soup = BeautifulSoup(html, 'html.parser')
    extracted_ids = []
    
    for a_tag in soup.find_all('a', title='Abstract'):
        href = a_tag.get('href', '')
        # Pastikan href adalah string sebelum split
        if href and isinstance(href, str):
            extracted_ids.append(href.split('/')[-1])
            
    return extracted_ids

async def fetch_page(client, url):
    """Fungsi pembantu untuk mengambil konten halaman dengan delay random."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    delay = random.uniform(5, 15) 
    await asyncio.sleep(delay)
    
    try:
        response = await client.get(url, headers=headers, timeout=30.0)
        if response.status_code == 200:
            ids = extract_id(response.text)
            print(f"Berhasil: {url} | Menemukan {len(ids)} ID")
            return ids
        elif response.status_code == 404:
            print(f"Error 404: Halaman tidak ditemukan -> {url}")
        elif response.status_code == 403:
            print(f"Error 403: Akses ditolak (IP Terblokir). Berhenti sejenak.")
        else:
            print(f"Gagal {response.status_code} pada {url}")
    except Exception as e:
        print(f"Exception pada {url}: {e}")
    
    return []


async def fetchArxivId(all_pages):
    results = {}
    async with httpx.AsyncClient() as client:
        for category, urls in all_pages.items():
            print(f"\n--- Memproses Kategori: {category} ---")
            category_ids = []
            
            for url in urls:
                ids = await fetch_page(client, url)
                category_ids.extend(ids)
            
            results[category] = list(set(category_ids))
        
        print("\n--- HASIL EKSTRAKSI ---")
        for cat, ids in results.items():
            print(f"Kategori {cat}: {len(ids)} ID ditemukan.")
            if ids:
                print(f"Found ID: {ids[:50]}")
                return ids[:10]

async def fetch_paper_details(client, arxiv_id):
    url = f"https://arxiv.org/abs/{arxiv_id}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        # Delay acak 2-5 detik agar tidak dianggap spammer oleh ArXiv
        await asyncio.sleep(random.uniform(20, 50))
        
        response = await client.get(url, headers=headers, timeout=30.0)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Ekstrak Judul
            title = soup.find('h1', class_='title mathjax')
            title_text = title.text.replace('Title:', " ").strip() if title else "N/A"
            
            # Ekstrak Author
            authors = soup.find('div', class_='authors')
            authors_text = authors.text.replace('Authors:', " ").strip() if authors else "N/A"
            
            # Ekstrak Abstrak
            abstract = soup.find('blockquote', class_='abstract mathjax')
            abstract_text = abstract.text.replace('Abstract:', " ").strip() if abstract else "N/A"
            
            # Ekstrak Tanggal Submit
            date_tag = soup.find('div', class_='dateline')
            date_text = date_tag.text.strip() if date_tag else "N/A"

            return {
                "id": arxiv_id,
                "title": title_text,
                "authors": authors_text,
                "abstract": abstract_text,
                "published_date": date_text,
                "url": url
            }
        else:
            print(f"Gagal mengambil detail ID {arxiv_id}. Status: {response.status_code}")
            return None
        
    except Exception as e:
        print(f"Error pada ID {arxiv_id}: {e}")
        return None

async def scrape_all_details(id_list):
    all_details = []
    
    async with httpx.AsyncClient() as client:
        print(f"\nMemulai scraping detail untuk {len(id_list)} paper...")
        
        for index, paper_id in enumerate(id_list):
            print(f"[{index+1}/{len(id_list)}] Mengambil detail: {paper_id}")
            
            detail = await fetch_paper_details(client, paper_id)
            if detail:
                all_details.append(detail)
                
    return all_details

def convert_to_csv():
    print("print")

async def main():
    parser = argparse.ArgumentParser(description='ArXiv advanced search scraper')
    parser.add_argument('--category', '-c', default='computer_science', help='classification to enable (e.g., computer_science, mathematics, physics)')
    parser.add_argument('--from-date', '-f', default='2025-12', help='from date in YYYY-MM or YYYY-MM-DD')
    parser.add_argument('--to-date', '-t', default='2026-01', help='to date in YYYY-MM or YYYY-MM-DD')
    parser.add_argument('--size', '-s', type=int, default=200, help='results per page')
    args = parser.parse_args()

    async with httpx.AsyncClient() as client:
        ids = await fetch_advanced_search(client, category=args.category, from_date=args.from_date, to_date=args.to_date, size=args.size)
        if not ids:
            print('No ids found from advanced search; falling back to category list scraping')
            all_pages = arxiv_pages(ARXIV_FIELDS)
            arxiv_id = await fetchArxivId(all_pages)
            ids = arxiv_id or []

    print('SCRAPPING RESULT:', ids)
    if ids:
        detail_paper = await scrape_all_details(ids[:50])
        print('Detail Paper', detail_paper)

if __name__ == "__main__":
    asyncio.run(main())