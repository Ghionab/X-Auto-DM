from crawl4ai import AsyncWebCrawler
import asyncio

GROUPS = {
    "Post & Action Endpoint V2": [
        "https://docs.twitterapi.io/api-reference/endpoint/user_login_v2",
        "https://docs.twitterapi.io/api-reference/endpoint/upload_media_v2",
        "https://docs.twitterapi.io/api-reference/endpoint/create_tweet_v2",
        "https://docs.twitterapi.io/api-reference/endpoint/get_dm_history_by_user_id",
        "https://docs.twitterapi.io/api-reference/endpoint/send_dm_v2",
        "https://docs.twitterapi.io/api-reference/endpoint/retweet_tweet_v2",
        "https://docs.twitterapi.io/api-reference/endpoint/delete_tweet_v2",
        "https://docs.twitterapi.io/api-reference/endpoint/follow_user_v2",
        "https://docs.twitterapi.io/api-reference/endpoint/unfollow_user_v2",
        "https://docs.twitterapi.io/api-reference/endpoint/like_tweet_v2",
        "https://docs.twitterapi.io/api-reference/endpoint/unlike_tweet_v2",
        "https://docs.twitterapi.io/api-reference/endpoint/create_community_v2",
        "https://docs.twitterapi.io/api-reference/endpoint/delete_community_v2",
        "https://docs.twitterapi.io/api-reference/endpoint/join_community_v2",
        "https://docs.twitterapi.io/api-reference/endpoint/leave_community_v2"
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
