import asyncio
import random
import httpx
from bs4 import BeautifulSoup


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
    all_pages = arxiv_pages(ARXIV_FIELDS)
    arxiv_id =  await fetchArxivId(all_pages)
    print("SCRAPPING RESULT:" , arxiv_id)
    detail_paper = await scrape_all_details(arxiv_id)
    
    print("Detail Paper" , detail_paper)

if __name__ == "__main__":
    asyncio.run(main())