from crawl4ai import AsyncWebCrawler
import asyncio

GROUPS = {
    "List Endpoint": [
        "https://docs.twitterapi.io/api-reference/endpoint/get_list_followers",
        "https://docs.twitterapi.io/api-reference/endpoint/get_list_members"
    ]
}

async def scrape_group(name, urls):
    async with AsyncWebCrawler(verbose=True) as crawler:
        results = await crawler.arun_many(urls=urls)

        filename = f"{name.replace(' ', '_').lower()}.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# {name}\n\n")
            for r in results:
                f.write(f"## {r.url}\n\n")
                f.write(r.markdown)
                f.write("\n\n---\n\n")

        print(f"✅ Saved {len(results)} pages to {filename}")

async def main():
    for group, urls in GROUPS.items():
        await scrape_group(group, urls)

asyncio.run(main())
