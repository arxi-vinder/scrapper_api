import asyncio
import random
from bs4 import BeautifulSoup
from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool
import httpx

from app.schemas.request.category_arxiv import CategoryArxivRequest
from app.utils.arxiv_helper import arxiv_pages, extract_id, fetchArxivId, save_to_csv, scrape_all_details


router = APIRouter(
    prefix="/arxiv",
)


@router.post("/categories")
async def generate_pages(data: CategoryArxivRequest):
    pages = arxiv_pages(data.arxiv_fields)
    return {
        "status": "success",
        "data": pages
    }


@router.post("/pages")
async def fetch_arxiv_pages(data:CategoryArxivRequest):
    pages = arxiv_pages(data.arxiv_fields)
    arxiv_ids = await fetchArxivId(pages)

    return {
        "status": "success",
        "data": arxiv_ids
    }

@router.post("/pages/content")
async def fetch_arxiv_content(data: CategoryArxivRequest):
    pages = arxiv_pages(data.arxiv_fields)

    arxiv_ids = await fetchArxivId(pages)  # ← LIST

    content = await scrape_all_details(arxiv_ids)

    return {
        "status": "success",
        "total_ids": len(arxiv_ids),
        "data": content
    }


@router.post("/save-csv")
async def save_csv(data: CategoryArxivRequest):
    pages = arxiv_pages(data.arxiv_fields)

    arxiv_ids = await fetchArxivId(pages)

    content = await scrape_all_details(arxiv_ids)

    await run_in_threadpool(save_to_csv, content)
    return {
        "status": "success",
        "saved_rows": len(content)
    }
