import asyncio
import random
from bs4 import BeautifulSoup
from fastapi import APIRouter
import httpx

from app.schemas.request.category_arxiv import CategoryArxivRequest
from app.utils.arxiv_helper import arxiv_pages, extract_id


router = APIRouter(
    prefix="/arxiv",
)


@router.post("/pages")
async def generate_pages(data: CategoryArxivRequest):
    pages = arxiv_pages(data.arxiv_fields)
    return {
        "status": "success",
        "data": pages
    }


