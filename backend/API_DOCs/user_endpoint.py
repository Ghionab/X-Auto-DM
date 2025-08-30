from crawl4ai import AsyncWebCrawler
import asyncio

GROUPS = {
    "User Endpoint": [
        "https://docs.twitterapi.io/api-reference/endpoint/batch_get_user_by_userids",
        "https://docs.twitterapi.io/api-reference/endpoint/get_user_by_username",
        "https://docs.twitterapi.io/api-reference/endpoint/get_user_last_tweets",
        "https://docs.twitterapi.io/api-reference/endpoint/get_user_followers",
        "https://docs.twitterapi.io/api-reference/endpoint/get_user_followings",
        "https://docs.twitterapi.io/api-reference/endpoint/get_user_mention",
        "https://docs.twitterapi.io/api-reference/endpoint/check_follow_relationship",
        "https://docs.twitterapi.io/api-reference/endpoint/search_user"
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
