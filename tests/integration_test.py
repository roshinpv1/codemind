import requests
import time
import json

BASE_URL = "http://localhost:8000"

def test_codemind_lifecycle():
    print("🚀 Starting CodeMind Integration Test Suite...\n")

    # 1. Setup Environment
    print("Step 1: Initializing Environment...")
    resp = requests.post(f"{BASE_URL}/setup")
    assert resp.status_code == 200
    print(f"✅ Setup: {resp.json()['status']}\n")

    # 2. Reset Data (Clean Slate)
    print("Step 2: Resetting System...")
    resp = requests.post(f"{BASE_URL}/reset")
    assert resp.status_code == 200
    print("✅ Reset Complete\n")

    # 3. Index a Repository
    print("Step 3: Triggering Indexing...")
    # Using a small repo for testing speed
    index_payload = {
        "repo_url": "https://github.com/vinta/awesome-python", 
        "branch": "master"
    }
    resp = requests.post(f"{BASE_URL}/index", json=index_payload)
    assert resp.status_code == 200
    index_id = resp.json()["index_id"]
    print(f"✅ Indexing Started: {index_id}")
    
    print("⌛ Waiting for indexing to complete (Polling /status)...")
    status = "started"
    while status == "started":
        time.sleep(2)
        status_resp = requests.get(f"{BASE_URL}/status/{index_id}")
        assert status_resp.status_code == 200
        status = status_resp.json()["status"]
        print(f"   Current Status: {status}")
        if status == "failed":
            print(f"❌ Indexing Failed: {status_resp.json()['error']}")
            assert False
    
    print(f"✅ Indexing Finished with status: {status}\n")

    # 4. Test Search (Semantic & Structural)
    print("Step 4: Testing Search Intelligence...")
    search_payload = {
        "query": "Where are audio libraries?",
        "repo": "awesome-python",
        "branch": "master"
    }
    resp = requests.post(f"{BASE_URL}/search", json=search_payload)
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) > 0
    
    top_result = results[0]
    print(f"✅ Search Found {len(results)} results")
    print(f"TOP RELEVANCE: {top_result['score']:.4f}")
    # Verify AST features are present
    assert "symbols" in top_result
    assert "calls" in top_result
    print(f"✅ AST Metadata Verified: {len(top_result['symbols'])} symbols found")
    
    # Check for structural boost
    boosted = [r for r in results if r.get("structural_boost")]
    if boosted:
        print(f"🔥 Hybrid Reranking Active: {len(boosted)} results received structural boost")
    print()

    # 5. Test RAG Execution
    print("Step 5: Testing RAG Execution (/execute)...")
    execute_payload = {
        "tenant": "test_user",
        "repo": "awesome-python",
        "branch": "master",
        "instruction": "Summarize what this repository offers for Web Frameworks based on the context.",
        "context_query": "web frameworks"
    }
    resp = requests.post(f"{BASE_URL}/execute", json=execute_payload)
    assert resp.status_code == 200
    print("✅ RAG Response Received")
    print(f"LLM OUTPUT SNIPPET: {resp.json()['result'][:200]}...\n")

    # 6. Verify Isolation
    print("Step 6: Verifying Repository Isolation...")
    search_payload_empty = {
        "query": "python",
        "repo": "non_existent_repo",
        "branch": "master"
    }
    resp = requests.post(f"{BASE_URL}/search", json=search_payload_empty)
    assert len(resp.json()["results"]) == 0
    print("✅ Repository Isolation Confirmed\n")

    print("🎉 Integration Test Suite Successful!")

if __name__ == "__main__":
    test_codemind_lifecycle()
