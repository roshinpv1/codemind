import os
import cocoindex
from dotenv import load_dotenv
load_dotenv()
cocoindex.init()

from cocoindex_app.search import search

try:
    print("Testing search...")
    res = search("how to create app", repo="fastapi")
    print(f"Found {len(res.results)} results")
    if res.results:
        print(f"Top result: {res.results[0]['filename']}")
except Exception as e:
    print(f"Search failed: {e}")
