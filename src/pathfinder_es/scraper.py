from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


@dataclass
class PageData:
    url: str
    title: str
    category: str
    content_en: str


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
                "User-Agent": "PathfinderESBot/0.1 (+internal-use, with-permission)",
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

            page = self._fetch_page(url)
            if page:
                yield page

                for link in self._extract_links(page.url):
                    if link not in seen:
                        queue.append(link)

            time.sleep(self.delay_s)

    def _fetch_page(self, url: str) -> PageData | None:
        response = self.session.get(url, timeout=self.timeout_s)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        title = (soup.title.string or "").strip() if soup.title else ""

        main = soup.select_one("main") or soup.select_one("#main") or soup.body
        if not main:
            return None

        for tag in main.select("script, style, nav, footer"):
            tag.decompose()

        text = "\n".join(line.strip() for line in main.get_text("\n").splitlines() if line.strip())
        if not text:
            return None

        return PageData(url=url, title=title, category=self._category_from_url(url), content_en=text)

    def _extract_links(self, base_url: str) -> list[str]:
        response = self.session.get(base_url, timeout=self.timeout_s)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")

        links: list[str] = []
        for anchor in soup.select("a[href]"):
            href = anchor.get("href")
            if not href:
                continue
            absolute = urljoin(base_url, href)
            parsed = urlparse(absolute)
            if parsed.scheme not in {"http", "https"}:
                continue
            if parsed.netloc != self.allowed_domain:
                continue
            normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if parsed.query:
                normalized += f"?{parsed.query}"
            links.append(normalized)

        return list(dict.fromkeys(links))

    @staticmethod
    def _category_from_url(url: str) -> str:
        path = urlparse(url).path.strip("/")
        if not path:
            return "home"
        return path.split("/")[0].lower()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
