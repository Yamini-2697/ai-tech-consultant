
import asyncio
import hashlib
from datetime import datetime, timezone
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from task1_knowledge_brain.database import (
    get_connection,
    initialize_database,
)

SITEMAP_URL = (
    "https://support.brilliantdirectories.com/support/sitemap.xml"
)

ALLOWED_HOST = "support.brilliantdirectories.com"


def extract_sitemap_urls(xml_text: str) -> list[str]:
    root = ET.fromstring(xml_text)
    urls = []

    for element in root.iter():
        if element.tag.endswith("loc") and element.text:
            url = element.text.strip()
            parsed = urlparse(url)

            if (
                parsed.scheme in {"http", "https"}
                and parsed.netloc.lower() == ALLOWED_HOST
            ):
                urls.append(url)

    return list(dict.fromkeys(urls))


async def fetch_article(client, url):
    response = await client.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    for element in soup.select(
        "script, style, nav, footer, header, noscript"
    ):
        element.decompose()

    title_tag = soup.find("h1") or soup.find("title")
    title = title_tag.get_text(" ", strip=True) if title_tag else url

    article = soup.find("article") or soup.find("main") or soup.body or soup
    content = article.get_text(" ", strip=True)

    if len(content) < 80:
        return None

    return {
        "url": url,
        "title": title,
        "content": content,
        "content_hash": hashlib.sha256(
            content.encode("utf-8")
        ).hexdigest(),
        "last_crawled": datetime.now(timezone.utc).isoformat(),
    }


async def crawl_help_center(max_articles=20):
    initialize_database()

    async with httpx.AsyncClient(
        timeout=20.0,
        follow_redirects=True,
        headers={"User-Agent": "AITechConsultant/1.0"},
    ) as client:
        response = await client.get(SITEMAP_URL)
        response.raise_for_status()

        urls = extract_sitemap_urls(response.text)[:max_articles]
        print(f"Found {len(urls)} URLs")

        for index, url in enumerate(urls, start=1):
            try:
                article = await fetch_article(client, url)

                if article is None:
                    print(f"Skipped: {url}")
                    continue

                with get_connection() as connection:
                    connection.execute(
                        """
                        INSERT INTO articles
                        (url, title, content, content_hash, last_crawled)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(url) DO UPDATE SET
                            title = excluded.title,
                            content = excluded.content,
                            content_hash = excluded.content_hash,
                            last_crawled = excluded.last_crawled
                        """,
                        (
                            article["url"],
                            article["title"],
                            article["content"],
                            article["content_hash"],
                            article["last_crawled"],
                        ),
                    )

                print(f"[{index}/{len(urls)}] Saved: {article['title']}")

            except (httpx.HTTPError, ValueError) as error:
                print(f"Failed: {url} - {error}")

            await asyncio.sleep(1)

    print("Crawling finished.")


if __name__ == "__main__":
    asyncio.run(crawl_help_center())
