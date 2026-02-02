import os
import asyncio
import cocoindex
from dotenv import load_dotenv
load_dotenv()
cocoindex.init()

from cocoindex_app.search import search

async def test():
    try:
        print("Testing search...")
        res = await search("how to create app", repo="fastapi")
        print(f"Found {len(res.results)} results")
        if res.results:
            print(f"Top result: {res.results[0]['filename']}")
    except Exception as e:
        print(f"Search failed: {e}")

if __name__ == "__main__":
    asyncio.run(test())
