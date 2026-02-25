from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup


@dataclass
class PageData:
    url: str
    title: str
    category: str
    subcategory: str
    content_text_en: str
    content_html_en: str


class AONScraper:
    def __init__(
        self,
        start_url: str = "https://2e.aonprd.com",
        allowed_domain: str = "2e.aonprd.com",
        delay_s: float = 1.0,
        timeout_s: int = 30,
        session: requests.Session | None = None,
    ) -> None:
        self.start_url = start_url.rstrip("/")
        self.allowed_domain = allowed_domain
        self.delay_s = delay_s
        self.timeout_s = timeout_s
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "PathfinderESBot/0.2 (+internal-use, with-permission)",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

    def crawl(self, max_pages: int = 100) -> Iterable[PageData]:
        seen: set[str] = set()
        queue: deque[str] = deque([self.start_url])

        while queue and len(seen) < max_pages:
            url = queue.popleft()
            if url in seen:
                continue
            seen.add(url)

            page, discovered_links = self._fetch_page(url)
            if page:
                yield page
                for link in discovered_links:
                    if link not in seen:
                        queue.append(link)

            time.sleep(self.delay_s)

    def _fetch_page(self, url: str) -> tuple[PageData | None, list[str]]:
        response = self.session.get(url, timeout=self.timeout_s)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        title = (soup.title.string or "").strip() if soup.title else ""

        main = soup.select_one("main") or soup.select_one("#main") or soup.body
        if not main:
            return None, []

        for tag in main.select("script, style"):
            tag.decompose()

        discovered_links = self._rewrite_and_collect_links(main=main, base_url=url)

        text = "\n".join(line.strip() for line in main.get_text("\n").splitlines() if line.strip())
        html = str(main)
        if not text:
            return None, discovered_links

        category, subcategory = self._categorize_url(url)
        return (
            PageData(
                url=url,
                title=title,
                category=category,
                subcategory=subcategory,
                content_text_en=text,
                content_html_en=html,
            ),
            discovered_links,
        )

    def _rewrite_and_collect_links(self, main, base_url: str) -> list[str]:
        links: list[str] = []

        for anchor in main.select("a[href]"):
            href = (anchor.get("href") or "").strip()
            if not href:
                continue

            absolute = urljoin(base_url, href)
            normalized = self._normalize_url(absolute)
            if not normalized:
                continue

            parsed = urlparse(normalized)
            if parsed.netloc == self.allowed_domain:
                links.append(normalized)
                anchor["href"] = "#"
                anchor["data-internal-url"] = normalized
            else:
                anchor["href"] = normalized
                anchor["target"] = "_blank"
                anchor["rel"] = "noopener noreferrer"

        return list(dict.fromkeys(links))

    def _normalize_url(self, url: str) -> str | None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return None

        query_pairs = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if not k.lower().startswith("utm_")]
        query = urlencode(query_pairs, doseq=True)

        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", query, ""))

    @staticmethod
    def _categorize_url(url: str) -> tuple[str, str]:
        parts = [p for p in urlparse(url).path.strip("/").split("/") if p]
        if not parts:
            return "home", "root"
        if len(parts) == 1:
            return parts[0].lower(), "general"
        return parts[0].lower(), parts[1].lower()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
