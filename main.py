import asyncio
import logging
import os

from contextlib import asynccontextmanager
from typing import Annotated, Optional, TypedDict
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from playwright.async_api import ElementHandle, Page, async_playwright
from pydantic import BaseModel


def verify_auth(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Missing or invalid authorization header"
        )
    token = auth_header.split(" ")[1]
    if token != request.app.state.access_token:
        raise HTTPException(status_code=403, detail="Invalid access token")


logging_level = logging.INFO
level = os.environ.get("LOGGING_LEVEL", "INFO").upper()
if level == "DEBUG":
    logging_level = logging.DEBUG
elif level == "WARNING":
    logging_level = logging.WARNING
elif level == "ERROR":
    logging_level = logging.ERROR
elif level == "CRITICAL":
    logging_level = logging.CRITICAL
elif level == "NOTSET":
    logging_level = logging.NOTSET
elif level == "FATAL":
    logging_level = logging.FATAL


# Configure logging
logging.basicConfig(
    level=logging_level,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    access_token = os.environ.get("ACCESS_TOKEN")
    if not access_token:
        raise ValueError("ACCESS_TOKEN environment variable is not set")
    logging.debug(f"Kagi authentication with access token: {access_token}")
    app.state.access_token = access_token
    token = os.environ.get("KAGI_TOKEN")
    if not token:
        raise ValueError("KAGI_TOKEN environment variable is not set")
    # Authenticate by token
    async with async_playwright() as p:
        async with await p.chromium.launch(headless=True) as browser:
            async with await browser.new_page() as page:
                await handle_token_authentication(page, token)
                cks = await page.context.cookies()
                app.state.cookies = cks
                logging.debug("Kagi authentication done.")
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*"
    ],  # Allow all origins, should be restricted to specific domains in production
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)


class SearchResult(TypedDict):
    title: str
    url: str
    snippet: str


async def handle_token_authentication(page: Page, token: str):
    await page.goto(f"https://kagi.com/search?token={token}")
    result = urlparse(page.url)
    if result.path != "/":
        raise ValueError("Invalid token or authentication failed")


async def perform_search(page: Page, query: str) -> Optional[list[SearchResult]]:
    await page.goto(f"https://kagi.com/search?q={query}")
    for _ in range(5):
        result = await page.query_selector(".results-box")
        if not result:
            logging.debug(f"Search results not found for query: {query}, retrying...")
            await asyncio.sleep(0.5)
            continue
        search_results = await result.query_selector_all(".search-result")
        if len(search_results) == 0:
            logging.debug(f"Search results not found for query: {query}, retrying...")
            await asyncio.sleep(0.5)
            continue
        return await parse_search_results(search_results)


async def parse_search_results(
    search_results: list[ElementHandle],
) -> list[SearchResult]:
    results = []
    for result in search_results:
        title = await result.query_selector(".__sri-title")
        if not title:
            logging.debug("Search result title not found, skipping...")
            continue
        title = await title.inner_text()
        url = await result.query_selector(".__sri-url-box")
        if not url:
            logging.debug("Search result URL not found, skipping...")
            continue
        url = await url.query_selector("a")
        if not url:
            logging.debug("Search result URL link not found, skipping...")
            continue
        url = await url.get_attribute("href")
        if not url:
            logging.debug("Search result URL attribute not found, skipping...")
            continue
        snippet = await result.query_selector(".__sri-desc")
        if not snippet:
            logging.debug("Search result snippet not found, skipping...")
            continue
        snippet = await snippet.inner_text()
        results.append({"title": title, "url": url, "snippet": snippet})
    return results


class SearchRequest(BaseModel):
    q: str


@app.get("/api/search")
async def search(
    query: Annotated[SearchRequest, Query()],
    _dep: None = Depends(verify_auth),
):
    async with async_playwright() as p:
        cookies = app.state.cookies
        async with await p.chromium.launch(headless=True) as browser:
            async with await browser.new_page() as page:
                await page.context.add_cookies(cookies)
                # Perform a search
                results = await perform_search(page, query.q)
    if not results:
        return {}
    return results
