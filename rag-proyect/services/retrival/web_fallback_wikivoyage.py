from __future__ import annotations

import re
from typing import List, Tuple
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup
from bs4.exceptions import FeatureNotFound
from retrival.country_detector import detect_country

BASE_URL = "https://es.wikivoyage.org"


def _make_soup(html: str) -> BeautifulSoup:
    """Crea un BeautifulSoup; usa `lxml` si está disponible y si no `html.parser`."""
    try:
        return BeautifulSoup(html or "", "lxml")
    except FeatureNotFound:
        return BeautifulSoup(html or "", "html.parser")


def _build_search_url(query: str) -> str:
    q = (query or "").strip()
    encoded = quote_plus(q)
    return (
        f"{BASE_URL}/w/index.php?search={encoded}"
        "&title=Special:Search&fulltext=1"
    )


def _http_get(url: str, timeout_seconds: int) -> str:
    resp = requests.get(
        url,
        timeout=timeout_seconds,
        headers={
            "User-Agent": "RAG-System-SRI/1.0 (school project; +https://example.invalid)"
        },
    )
    resp.raise_for_status()
    return resp.text


def _extract_result_urls(search_html: str, max_pages: int) -> List[str]:
    soup = _make_soup(search_html)

    urls: List[str] = []
    seen: set[str] = set()

    for a in soup.find_all("a", href=True):
        href = a.get("href")
        if not href:
            continue
        if "#" in href:
            continue
        if not href.startswith("/wiki/"):
            continue

        title = (a.get_text() or "").strip()
        # Excluye namespaces (Special:, Help:, File:, Category:, etc.).
        if ":" in title:
            continue

        full = urljoin(BASE_URL, href)
        if full in seen:
            continue

        seen.add(full)
        urls.append(full)
        if len(urls) >= max_pages:
            break

    return urls


def _extract_page_text(page_html: str) -> Tuple[str, str]:
    soup = _make_soup(page_html)

    h1 = soup.find("h1", id="firstHeading")
    title = (h1.get_text() if h1 else "").strip()

    content = soup.select_one("#mw-content-text")
    if content is None:
        return title, ""

    # Remueve bloques típicamente ruidosos.
    for selector in ("table", "nav", "sup", "style", "script"):
        for el in content.select(selector):
            el.decompose()

    paragraphs = []
    for p in content.find_all("p"):
        txt = p.get_text(" ", strip=True)
        if txt:
            paragraphs.append(txt)

    text = "\n\n".join(paragraphs)
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) > 40_000:
        text = text[:40_000]

    return title, text


def fetch_wikivoyage_pages(query: str, max_pages: int, timeout_seconds: int) -> list[dict]:
    """Busca páginas en Wikivoyage y retorna documentos normalizados."""
    try:
        q = (query or "").strip()
        if not q:
            return []

        max_pages_int = int(max_pages)
        if max_pages_int <= 0:
            return []

        timeout_int = int(timeout_seconds)
        if timeout_int <= 0:
            timeout_int = 20

        search_url = _build_search_url(q)
        search_html = _http_get(search_url, timeout_seconds=timeout_int)
        result_urls = _extract_result_urls(search_html, max_pages=max_pages_int)

        docs: list[dict] = []
        for url in result_urls:
            page_html = _http_get(url, timeout_seconds=timeout_int)
            title, text = _extract_page_text(page_html)
            if not text:
                continue

            sample_for_detection = f"{title} {text[:2000]}"
            detected_country = detect_country(sample_for_detection)

            docs.append(
                {
                    "text": text,
                    "metadata": {
                        "title": title,
                        "url": url,
                        "source": "wikivoyage",
                        "pais": detected_country,
                    },
                }
            )

        return docs
    except Exception:
        return []
