import asyncio
from datetime import datetime
import os
import random
from typing import Any, Dict, List
from bs4 import BeautifulSoup
import httpx
import pandas as pd

DATA_DIR = "data"
CSV_FILENAME = "arxiv_papers_daily.csv"
CSV_PATH = os.path.join(DATA_DIR, CSV_FILENAME)

os.makedirs(DATA_DIR, exist_ok=True)

def arxiv_pages(fields:dict):
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
    
    delay = random.uniform(5, 10) 
    await asyncio.sleep(delay)
    
    try:
        response = await client.get(url, headers=headers, timeout=12.0)
        if response.status_code == 200:
            ids = extract_id(response.text)
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
    all_ids = []

    async with httpx.AsyncClient() as client:
        for urls in all_pages.values():
            for url in urls:
                ids = await fetch_page(client, url)
                all_ids.extend(ids)

    return list(set(all_ids))


async def fetch_paper_details(client, arxiv_id):
    url = f"https://arxiv.org/abs/{arxiv_id}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        # Delay acak 2-5 detik agar tidak dianggap spammer oleh ArXiv
        await asyncio.sleep(random.uniform(10, 20))
        
        response = await client.get(url, headers=headers, timeout=12.0)
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
            return None
        
    except Exception as e:
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

def save_to_csv(new_data: List[Dict[str, Any]]) -> None:
    if not new_data:
        return

    new_df = pd.DataFrame(new_data)
    new_df["last_updated"] = datetime.now()

    if os.path.exists(CSV_PATH):
        old_df = pd.read_csv(CSV_PATH)
        df = pd.concat([old_df, new_df], ignore_index=True)
    else:
        df = new_df

    df = df.drop_duplicates(subset="id", keep="last")
    df.to_csv(CSV_PATH, index=False)