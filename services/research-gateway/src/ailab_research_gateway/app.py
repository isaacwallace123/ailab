import hmac
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated, Any, Literal, Self
from urllib.parse import urlsplit

import aiohttp
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from .fetch import (
    EXTRACT_CONTENT_TYPES,
    TEXT_CONTENT_TYPES,
    ControlledFetcher,
    FetchPolicyError,
    UpstreamFetchError,
    extract_readable_text,
)


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    api_key: str
    docling_api_key: str
    docling_url: str = "http://docling:5001"
    searxng_url: str = "http://searxng:8080"
    max_response_bytes: int = 25 * 1024 * 1024
    max_text_chars: int = 100_000
    max_redirects: int = 5
    timeout_seconds: float = 30.0
    max_concurrency: int = 4
    user_agent: str = "AI-Lab-Research-Gateway/0.1 (+private research assistant)"

    @classmethod
    def from_environment(cls) -> Self:
        return cls(
            api_key=os.environ.get("RESEARCH_GATEWAY_API_KEY", ""),
            docling_api_key=os.environ.get("DOCLING_API_KEY", ""),
            docling_url=os.environ.get("DOCLING_URL", "http://docling:5001").rstrip("/"),
            searxng_url=os.environ.get("SEARXNG_URL", "http://searxng:8080").rstrip("/"),
            max_response_bytes=int(
                os.environ.get("RESEARCH_MAX_RESPONSE_BYTES", str(25 * 1024 * 1024))
            ),
            max_text_chars=int(os.environ.get("RESEARCH_MAX_TEXT_CHARS", "100000")),
            max_redirects=int(os.environ.get("RESEARCH_MAX_REDIRECTS", "5")),
            timeout_seconds=float(os.environ.get("RESEARCH_TIMEOUT_SECONDS", "30")),
            max_concurrency=int(os.environ.get("RESEARCH_MAX_CONCURRENCY", "4")),
        )

    def validate_secrets(self) -> None:
        if len(self.api_key) < 40 or len(self.docling_api_key) < 40:
            raise RuntimeError("strong gateway and Docling API keys are required")
        search_url = urlsplit(self.searxng_url)
        if search_url.scheme != "http" or not search_url.hostname:
            raise RuntimeError("SearXNG must use a fixed internal HTTP service URL")


class URLRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str = Field(min_length=8, max_length=4096)


class FetchResponse(BaseModel):
    requested_url: str
    final_url: str
    retrieved_at: datetime
    status_code: int
    content_type: str
    byte_count: int
    sha256: str
    title: str
    text: str


class ExtractResponse(BaseModel):
    source: dict[str, Any]
    extraction: dict[str, Any]


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=2, max_length=500)
    categories: Literal["general", "news", "science", "files"] = "general"
    language: str = Field(default="en", pattern=r"^(all|[A-Za-z]{2,3}(?:-[A-Za-z]{2})?)$")
    time_range: Literal["day", "month", "year"] | None = None
    count: int = Field(default=8, ge=1, le=10)


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    engines: list[str]
    category: str | None = None
    published_at: str | None = None
    score: float | None = None


class SearchResponse(BaseModel):
    query: str
    retrieved_at: datetime
    results: list[SearchResult]
    unresponsive_engines: list[str]


def normalize_search_results(body: dict[str, Any], count: int) -> list[SearchResult]:
    results: list[SearchResult] = []
    for item in body.get("results", []):
        if not isinstance(item, dict):
            continue
        raw_url = str(item.get("url", "")).strip()
        parsed = urlsplit(raw_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            continue
        raw_engines = item.get("engines") or [item.get("engine")]
        engines = [str(engine) for engine in raw_engines if engine]
        score = item.get("score")
        results.append(
            SearchResult(
                title=str(item.get("title") or raw_url)[:500],
                url=raw_url,
                snippet=str(item.get("content") or "")[:4000],
                engines=engines,
                category=str(item["category"]) if item.get("category") else None,
                published_at=(
                    str(item["publishedDate"]) if item.get("publishedDate") else None
                ),
                score=float(score) if isinstance(score, int | float) else None,
            )
        )
        if len(results) >= count:
            break
    return results


def normalize_unresponsive_engines(body: dict[str, Any]) -> list[str]:
    normalized: list[str] = []
    for item in body.get("unresponsive_engines", []):
        if isinstance(item, list | tuple) and item:
            normalized.append(str(item[0]))
        elif item:
            normalized.append(str(item))
    return sorted(set(normalized))


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or Settings.from_environment()
    app_settings.validate_secrets()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        fetcher = ControlledFetcher(
            max_bytes=app_settings.max_response_bytes,
            max_redirects=app_settings.max_redirects,
            timeout_seconds=app_settings.timeout_seconds,
            max_concurrency=app_settings.max_concurrency,
            user_agent=app_settings.user_agent,
        )
        await fetcher.start()
        docling_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=180),
            trust_env=False,
        )
        searxng_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=app_settings.timeout_seconds),
            trust_env=False,
        )
        app.state.fetcher = fetcher
        app.state.docling_session = docling_session
        app.state.searxng_session = searxng_session
        yield
        await searxng_session.close()
        await docling_session.close()
        await fetcher.close()

    app = FastAPI(
        title="AI Lab Research Gateway",
        version="0.2.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )

    def authenticate(x_api_key: Annotated[str | None, Header()] = None) -> None:
        if x_api_key is None or not hmac.compare_digest(x_api_key, app_settings.api_key):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/fetch", response_model=FetchResponse)
    async def fetch_public_page(
        payload: URLRequest,
        _: Annotated[None, Depends(authenticate)],
        request: Request,
    ):
        try:
            document = await request.app.state.fetcher.retrieve(payload.url, TEXT_CONTENT_TYPES)
            title, text = extract_readable_text(
                document.content,
                document.content_type,
                app_settings.max_text_chars,
            )
        except FetchPolicyError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except UpstreamFetchError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return FetchResponse(
            requested_url=document.requested_url,
            final_url=document.final_url,
            retrieved_at=datetime.now(UTC),
            status_code=document.status_code,
            content_type=document.content_type,
            byte_count=len(document.content),
            sha256=document.sha256,
            title=title,
            text=text,
        )

    @app.post("/v1/search", response_model=SearchResponse)
    async def search_public_web(
        payload: SearchRequest,
        _: Annotated[None, Depends(authenticate)],
        request: Request,
    ):
        parameters: dict[str, str | int] = {
            "q": payload.query.strip(),
            "format": "json",
            "categories": payload.categories,
            "language": payload.language,
            "safesearch": 1,
        }
        if payload.time_range:
            parameters["time_range"] = payload.time_range
        try:
            async with request.app.state.searxng_session.get(
                f"{app_settings.searxng_url}/search",
                params=parameters,
            ) as response:
                body = await response.json(content_type=None)
                if response.status != 200 or not isinstance(body, dict):
                    raise HTTPException(status_code=502, detail="private search failed")
        except HTTPException:
            raise
        except (aiohttp.ClientError, TimeoutError, ValueError) as exc:
            raise HTTPException(status_code=502, detail="private search unavailable") from exc
        return SearchResponse(
            query=payload.query.strip(),
            retrieved_at=datetime.now(UTC),
            results=normalize_search_results(body, payload.count),
            unresponsive_engines=normalize_unresponsive_engines(body),
        )

    @app.post("/v1/extract", response_model=ExtractResponse)
    async def fetch_and_extract(
        payload: URLRequest,
        _: Annotated[None, Depends(authenticate)],
        request: Request,
    ):
        try:
            document = await request.app.state.fetcher.retrieve(payload.url, EXTRACT_CONTENT_TYPES)
        except FetchPolicyError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except UpstreamFetchError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        form = aiohttp.FormData()
        form.add_field(
            "files",
            document.content,
            filename=document.filename,
            content_type=document.content_type,
        )
        form.add_field("to_formats", "md")
        form.add_field("do_ocr", "true")
        form.add_field("table_mode", "accurate")
        try:
            async with request.app.state.docling_session.post(
                f"{app_settings.docling_url}/v1/convert/file",
                headers={"X-Api-Key": app_settings.docling_api_key},
                data=form,
            ) as response:
                body = await response.json(content_type=None)
                if response.status != 200:
                    raise HTTPException(status_code=502, detail="document extraction failed")
        except (aiohttp.ClientError, TimeoutError, ValueError) as exc:
            raise HTTPException(status_code=502, detail="document extraction unavailable") from exc
        return ExtractResponse(
            source={
                "requested_url": document.requested_url,
                "final_url": document.final_url,
                "retrieved_at": datetime.now(UTC).isoformat(),
                "content_type": document.content_type,
                "byte_count": len(document.content),
                "sha256": document.sha256,
            },
            extraction=body,
        )

    return app
