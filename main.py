import asyncio
import logging
import os

from contextlib import asynccontextmanager
from http import HTTPStatus
from typing import Annotated, Any, Dict, Optional, Union
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastmcp import FastMCP
from fastmcp.server.auth.auth import OAuthProvider
from mcp.server.auth.provider import AccessToken
from playwright.async_api import ElementHandle, Page, async_playwright
from pydantic import BaseModel, Field


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


class AccessTokenProvider(OAuthProvider):
    """A simple OAuth provider that uses an access token for authentication."""

    async def load_access_token(self, token: str):
        if token != app.state.access_token:
            return None
        return AccessToken(token=token, scopes=["search"], client_id="kagi_client")

    # --- Unused OAuth server methods ---
    async def get_client(self, client_id: str):
        raise NotImplementedError("Client management not supported")

    async def register_client(self, client_info):
        raise NotImplementedError("Client registration not supported")

    async def authorize(self, client, params) -> str:
        raise NotImplementedError("Authorization flow not supported")

    async def load_authorization_code(self, client, authorization_code: str):
        raise NotImplementedError("Authorization code flow not supported")

    async def exchange_authorization_code(self, client, authorization_code):
        raise NotImplementedError("Authorization code exchange not supported")

    async def load_refresh_token(self, client, refresh_token):
        raise NotImplementedError("Refresh token flow not supported")

    async def exchange_refresh_token(
        self,
        client,
        refresh_token,
        scopes: list[str],
    ):
        raise NotImplementedError("Refresh token exchange not supported")

    async def revoke_token(
        self,
        token,
    ) -> None:
        raise NotImplementedError("Token revocation not supported")


def create_mcp_server(app: FastAPI):
    mcp = FastMCP.from_fastapi(app=app)

    mcp.auth = AccessTokenProvider(issuer_url="https://kagi.com")

    mcp_app = mcp.http_app(transport="streamable-http")

    app.mount("/", mcp_app)
    return mcp_app.lifespan(mcp_app)


def verify_auth(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not (
        auth_header.startswith("Bot ") or auth_header.startswith("Bearer ")
    ):
        raise HTTPException(
            status_code=401, detail="Missing or invalid authorization header"
        )
    token = auth_header.split(" ")[1]
    if token != request.app.state.access_token:
        raise HTTPException(status_code=403, detail="Invalid access token")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with create_mcp_server(app):
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


class ExceptionResponse(BaseModel):
    error: str = Field(..., description="Error message")
    code: int = Field(..., description="HTTP status code")


default_responses: Dict[Union[int, str], Dict[str, Any]] = {
    "default": {
        "model": ExceptionResponse,
        "description": "An unexpected error occurred",
    }
}


@app.exception_handler(Exception)
async def exception_handler(_: Request, exc: Exception):
    """Global exception handler"""
    if isinstance(exc, HTTPException):
        code = exc.status_code or HTTPStatus.INTERNAL_SERVER_ERROR
        return JSONResponse(
            status_code=code,
            content=ExceptionResponse(error=str(exc), code=code).model_dump(),
        )
    return JSONResponse(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        content=ExceptionResponse(
            error=str(exc), code=HTTPStatus.INTERNAL_SERVER_ERROR
        ).model_dump(),
    )


class SearchResult(BaseModel):
    title: str = Field(..., description="Title of the search result")
    url: str = Field(..., description="URL of the search result")
    snippet: str = Field(..., description="Snippet of the search result")


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
        results.append({"title": title, "url": url, "snippet": snippet, "t": 0})
    return results


class SearchRequest(BaseModel):
    q: str = Field(..., description="Search query")


class SearchResponse(BaseModel):
    data: list[SearchResult] = Field(..., description="List of search results")


async def _search(query: str):
    async with async_playwright() as p:
        cookies = app.state.cookies
        async with await p.chromium.launch(headless=True) as browser:
            async with await browser.new_page() as page:
                await page.context.add_cookies(cookies)
                # Perform a search
                results = await perform_search(page, query)
    if not results:
        return {"data": []}
    return {"data": results}


@app.get(
    "/api/v0/search",
    operation_id="search",
    response_model=SearchResponse,
    responses=default_responses,
)
async def search(
    query: Annotated[SearchRequest, Query()],
    _dep: None = Depends(verify_auth),
):
    """Perform a search action"""
    return await _search(query.q)


class GetTimeResponse(BaseModel):
    time: str = Field(..., description="Current server time in ISO8601 format (UTC)")


@app.get(
    "/api/time",
    operation_id="time",
    response_model=GetTimeResponse,
    responses=default_responses,
)
async def get_time():
    """Get the current time in ISO8601 format (UTC)"""
    import datetime

    now = (
        datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    return {"time": now}


class FetchRequest(BaseModel):
    url: str = Field(..., description="URL to fetch page content from")


class FetchResponse(BaseModel):
    content: str = Field(..., description="Fetched page content in markdown format")


@app.get(
    "/api/fetch",
    operation_id="fetch",
    response_model=FetchResponse,
    responses=default_responses,
)
async def fetch(
    query: Annotated[FetchRequest, Query()], _dep: None = Depends(verify_auth)
):
    """Fetch page content by URL"""
    async with async_playwright() as p:
        async with await p.chromium.launch(headless=True) as browser:
            async with await browser.new_page() as page:
                await page.goto(query.url)
                content = await page.content()
    if not content:
        return {"content": ""}

    from markdownify import markdownify as md

    return {"content": md(content, strip=["script", "style", "header", "footer"])}
