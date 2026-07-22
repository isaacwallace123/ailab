from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import re
import socket
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import PurePosixPath
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit

import aiohttp
from aiohttp.abc import AbstractResolver

ALLOWED_PORTS = {80, 443}
REDIRECT_STATUSES = {301, 302, 303, 307, 308}
TEXT_CONTENT_TYPES = {"text/html", "application/xhtml+xml", "text/plain", "text/markdown"}
EXTRACT_CONTENT_TYPES = TEXT_CONTENT_TYPES | {
    "application/pdf",
    "application/json",
    "application/xml",
    "text/csv",
    "text/xml",
    "image/bmp",
    "image/jpeg",
    "image/png",
    "image/tiff",
    "image/webp",
    "application/msword",
    "application/vnd.ms-excel",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
FILENAME_EXTENSIONS = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "text/html": ".html",
    "application/xhtml+xml": ".html",
    "text/plain": ".txt",
    "text/csv": ".csv",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/tiff": ".tiff",
    "image/webp": ".webp",
}


class FetchPolicyError(ValueError):
    pass


class UpstreamFetchError(RuntimeError):
    pass


def require_public_ip(value: str) -> str:
    address = ipaddress.ip_address(value.split("%", 1)[0])
    if not address.is_global:
        raise FetchPolicyError(f"destination address is not globally routable: {address}")
    return str(address)


def normalize_public_url(value: str) -> str:
    if not value or len(value) > 4096:
        raise FetchPolicyError("URL is empty or too long")
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise FetchPolicyError("URL has an invalid port or authority") from exc
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        raise FetchPolicyError("only http and https URLs are allowed")
    if parsed.username is not None or parsed.password is not None:
        raise FetchPolicyError("credentials in URLs are not allowed")
    if not parsed.hostname:
        raise FetchPolicyError("URL must include a hostname")
    if port is not None and port not in ALLOWED_PORTS:
        raise FetchPolicyError("only ports 80 and 443 are allowed")

    host = parsed.hostname.rstrip(".")
    try:
        normalized_host = host.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise FetchPolicyError("hostname cannot be normalized") from exc
    try:
        ipaddress.ip_address(normalized_host)
    except ValueError:
        pass
    else:
        normalized_host = require_public_ip(normalized_host)

    bracketed_host = f"[{normalized_host}]" if ":" in normalized_host else normalized_host
    netloc = bracketed_host if port is None else f"{bracketed_host}:{port}"
    return urlunsplit((scheme, netloc, parsed.path or "/", parsed.query, ""))


class PublicOnlyResolver(AbstractResolver):
    async def resolve(
        self,
        host: str,
        port: int = 0,
        family: int = socket.AF_UNSPEC,
    ) -> list[dict[str, object]]:
        loop = asyncio.get_running_loop()
        try:
            records = await loop.getaddrinfo(
                host,
                port,
                family=family,
                type=socket.SOCK_STREAM,
            )
        except socket.gaierror as exc:
            raise OSError(f"DNS resolution failed for {host}") from exc
        resolved: list[dict[str, object]] = []
        seen: set[tuple[int, str]] = set()
        for address_family, _socktype, protocol, _canonname, sockaddr in records:
            address = require_public_ip(sockaddr[0])
            key = (address_family, address)
            if key in seen:
                continue
            seen.add(key)
            resolved.append(
                {
                    "hostname": host,
                    "host": address,
                    "port": port,
                    "family": address_family,
                    "proto": protocol,
                    "flags": socket.AI_NUMERICHOST,
                }
            )
        if not resolved:
            raise OSError(f"DNS resolution returned no public addresses for {host}")
        return resolved

    async def close(self) -> None:
        return None


@dataclass(frozen=True)
class RetrievedDocument:
    requested_url: str
    final_url: str
    status_code: int
    content_type: str
    content: bytes
    sha256: str
    filename: str


def safe_filename(url: str, content_type: str) -> str:
    candidate = unquote(PurePosixPath(urlsplit(url).path).name)
    candidate = re.sub(r"[^A-Za-z0-9._-]+", "-", candidate).strip(".-")
    extension = FILENAME_EXTENSIONS.get(content_type, ".bin")
    if not candidate:
        return f"document{extension}"
    if "." not in candidate:
        return f"{candidate}{extension}"
    return candidate[:160]


class ReadableHTMLParser(HTMLParser):
    _hidden_tags = {"script", "style", "noscript", "svg", "canvas", "template", "form"}
    _block_tags = {
        "article",
        "aside",
        "blockquote",
        "br",
        "dd",
        "div",
        "dl",
        "dt",
        "figcaption",
        "figure",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "li",
        "main",
        "nav",
        "ol",
        "p",
        "pre",
        "section",
        "table",
        "td",
        "th",
        "tr",
        "ul",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._hidden_depth = 0
        self._in_title = False
        self._title_parts: list[str] = []
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        tag = tag.lower()
        if tag in self._hidden_tags:
            self._hidden_depth += 1
        if tag == "title":
            self._in_title = True
        if not self._hidden_depth and tag in self._block_tags:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self._in_title = False
        if tag in self._hidden_tags and self._hidden_depth:
            self._hidden_depth -= 1
        if not self._hidden_depth and tag in self._block_tags:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)
        if not self._hidden_depth:
            self._parts.append(data)

    @staticmethod
    def _clean(parts: list[str]) -> str:
        value = " ".join(" ".join(parts).split())
        return re.sub(r"\s*\n\s*", "\n", value).strip()

    @property
    def title(self) -> str:
        return " ".join(" ".join(self._title_parts).split()).strip()

    @property
    def text(self) -> str:
        lines = []
        for part in "".join(self._parts).splitlines():
            line = " ".join(part.split())
            if line:
                lines.append(line)
        return "\n".join(lines)


def extract_readable_text(content: bytes, content_type: str, max_chars: int) -> tuple[str, str]:
    decoded = content.decode("utf-8", errors="replace")
    if content_type in {"text/html", "application/xhtml+xml"}:
        parser = ReadableHTMLParser()
        parser.feed(decoded)
        return parser.title[:500], parser.text[:max_chars]
    return "", decoded[:max_chars]


class ControlledFetcher:
    def __init__(
        self,
        *,
        max_bytes: int,
        max_redirects: int,
        timeout_seconds: float,
        max_concurrency: int,
        user_agent: str,
    ) -> None:
        self.max_bytes = max_bytes
        self.max_redirects = max_redirects
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._session: aiohttp.ClientSession | None = None

    async def start(self) -> None:
        timeout = aiohttp.ClientTimeout(
            total=self.timeout_seconds,
            connect=min(8.0, self.timeout_seconds),
            sock_connect=min(8.0, self.timeout_seconds),
            sock_read=min(15.0, self.timeout_seconds),
        )
        connector = aiohttp.TCPConnector(
            resolver=PublicOnlyResolver(),
            ttl_dns_cache=0,
            limit=16,
            limit_per_host=4,
        )
        self._session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            trust_env=False,
            auto_decompress=True,
            headers={"User-Agent": self.user_agent, "Accept": "*/*"},
        )

    async def close(self) -> None:
        if self._session is not None:
            await self._session.close()

    async def retrieve(self, url: str, allowed_content_types: set[str]) -> RetrievedDocument:
        if self._session is None:
            raise RuntimeError("fetcher has not started")
        requested_url = normalize_public_url(url)
        current_url = requested_url
        async with self._semaphore:
            for redirect_count in range(self.max_redirects + 1):
                current_url = normalize_public_url(current_url)
                try:
                    async with self._session.get(current_url, allow_redirects=False) as response:
                        if response.status in REDIRECT_STATUSES:
                            if redirect_count >= self.max_redirects:
                                raise FetchPolicyError("redirect limit exceeded")
                            location = response.headers.get("Location")
                            if not location:
                                raise UpstreamFetchError("redirect response omitted Location")
                            current_url = urljoin(current_url, location)
                            continue
                        if response.status < 200 or response.status >= 300:
                            raise UpstreamFetchError(f"upstream returned HTTP {response.status}")
                        content_type = response.headers.get("Content-Type", "")
                        content_type = content_type.split(";", 1)[0].strip().lower()
                        if content_type not in allowed_content_types:
                            raise FetchPolicyError(
                                f"content type is not allowed: {content_type or 'missing'}"
                            )
                        declared_size = response.content_length
                        if declared_size is not None and declared_size > self.max_bytes:
                            raise FetchPolicyError("declared response size exceeds the limit")
                        chunks: list[bytes] = []
                        received = 0
                        async for chunk in response.content.iter_chunked(64 * 1024):
                            received += len(chunk)
                            if received > self.max_bytes:
                                raise FetchPolicyError("downloaded response exceeds the limit")
                            chunks.append(chunk)
                        content = b"".join(chunks)
                        return RetrievedDocument(
                            requested_url=requested_url,
                            final_url=current_url,
                            status_code=response.status,
                            content_type=content_type,
                            content=content,
                            sha256=hashlib.sha256(content).hexdigest(),
                            filename=safe_filename(current_url, content_type),
                        )
                except (TimeoutError, aiohttp.ClientError, OSError) as exc:
                    raise UpstreamFetchError(
                        f"public retrieval failed: {type(exc).__name__}"
                    ) from exc
        raise FetchPolicyError("redirect limit exceeded")
