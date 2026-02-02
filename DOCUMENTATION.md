    # CodeMind: Semantic Code Indexing & RAG System

    CodeMind is a high-performance backend system designed to index source code repositories, generate semantic embeddings, and provide context-aware reasoning via Large Language Models (LLM). It enables developers to perform semantic search across large codebases and build RAG (Retrieval-Augmented Generation) applications.

    ## 🚀 Key Features

    ### 1. Advanced Code Indexing
    - **Recursive Discovery**: Recursively indexes repository files including `.py`, `.md`, `.rs`, `.toml`, `.js`, `.java`, `.go`, and more.
    - **Semantic Chunking**: Uses Tree-sitter aware recursive splitting to maintain code context within chunks.
    - **Full AST Parsing**: Uses `tree-sitter` to perform deep analysis of definitions (classes, functions) and call sites.
    - **Structural Metadata**: Captures symbols, function calls, and scopes to enable advanced structural search.
    - **Non-Blocking Execution**: Indexing runs in the background, providing immediate task IDs and status polling.

    ### 2. Multi-Storage Architecture
    - **PostgreSQL (pgvector)**: Standard relational storage for metadata and vector search.
    - **LanceDB**: High-performance, serverless vector database associated with local files.
    - **SQLite**: Local relational database for metadata (ideal for pairing with LanceDB).
    - **FAISS (Vector Store)**: High-speed local search using optimized vector indices on disk.
    - **MongoDB (Metadata Store)**: Flexible document storage for repository status and indexing logs.

    ### 3. Unified LLM Provider
    - **Local Drivers**: Support for LMStudio (OpenAI-compatible) and Ollama.
    - **Enterprise Drivers**: Support for Organizational LLMs (Enterprise API).
    - **Apigee Integration**: Enterprise-grade OAuth 2.0 security, automated token management, and custom request headers.
    - **Dynamic Factory**: Automatically selects the best available provider based on environment configuration.

    ### 4. Hybrid Semantic Search
    - **NLP Queries**: Search code using natural language.
    - **Structural Boosting**: Vector similarity search enhanced by exact matches on AST symbols (definitions) and calls.
    - **Cross-Backend Search**: Seamlessly switches search logic between PostgreSQL and FAISS/MongoDB.

    ## 🏗️ System Architecture

    ```mermaid
    graph TD
        Client[Client/UI/CI] -->|REST API| FastAPI[FastAPI Layer]
        
        subgraph "Indexing Service"
            FastAPI -->|Index Request| Git[Git Manager]
            Git -->|Clone/Pull| LocalRepo[(Local Repo Cache)]
            LocalRepo -->|Read| Flow[CocoIndex Flow]
            Flow -->|Chunk/Embed/AST| Embed[Sentence Transformers + Tree-sitter]
        end
        
        subgraph "Storage Layer"
            Flow -->|Upsert| DB[(PostgreSQL + pgvector)]
            Flow -->|Sync| FAISS[(FAISS Index)]
            Flow -->|Status| Mongo[(MongoDB)]
        end
        
        subgraph "Reasoning & Search"
            FastAPI -->|Search Query| Search[Search Engine]
            Search -->|Vector + AST Query| DB
            Search -->|Local Search| FAISS
            
            FastAPI -->|Execute/RAG| Engine[Reasoning Engine]
            Engine -->|Resolve Context| Search
            Engine -->|Prompt + Context| Factory[LLM Factory]
            Factory -->|Provider Selection| LLM[Apigee / Local / Enterprise]
        end
    ```


    ## 🛠️ Configuration (.env)

    ### Embedding Model (New)
    To support local execution and offline capabilities, you can load SentenceTransformer models from a local directory.
    ```env
    # Path to local HuggingFace model directory or HuggingFace model ID
    EMBEDDING_MODEL_PATH=/path/to/local/model/folder
    # Default: sentence-transformers/all-MiniLM-L6-v2
    ```

    ### Backend Storage
    ```env
    STORAGE_BACKEND=postgres  # Options: postgres, faiss_mongo, lancedb
    LANCEDB_URI=./data/lancedb  # Path to local LanceDB (if selected)
    
    METADATA_STORE=sqlite # Options: postgres, mongo, sqlite
    SQLITE_DB_PATH=./data/codemind.db
    
    COCOINDEX_DATABASE_URL=postgresql://user:pass@localhost:5432/codemind
    MONGODB_URI=mongodb://localhost:27017/codemind
    FAISS_INDEX_PATH=./data/faiss_index
    CODEBASE_ROOT=./data/repos
    ```

    ### LLM Provider
    ```env
    LLM_PROVIDER=local  # Options: local, ollama, apigee, enterprise

    # Local (LMStudio / OpenAI-compatible)
    LOCAL_LLM_URL=http://localhost:1234/v1
    LOCAL_LLM_MODEL=google/gemma-3n-e4b

    # Ollama
    OLLAMA_HOST=http://localhost:11434
    OLLAMA_MODEL=llama-3.2-3b-instruct

    # Apigee (Organization)
    APIGEE_NONPROD_LOGIN_URL=https://...
    APIGEE_CONSUMER_KEY=...
    APIGEE_CONSUMER_SECRET=...
    ENTERPRISE_BASE_URL=https://...
    WF_USE_CASE_ID=...
    WF_CLIENT_ID=...
    WF_API_KEY=...
    ```

    ## 📡 API Reference

    ### 1. Setup Environment
    **POST** `/setup`
    Initializes database extensions, creates status tables, and ensures directory structures are ready.

    ### 2. Index Repository
    **POST** `/index`
    ```json
    {
    "repo_url": "https://github.com/org/repo.git",
    "branch": "main"
    }
    ```
    **Response:**
    ```json
    {
    "index_id": "uuid",
    "status": "indexing_started",
    "message": "The codebase is being indexed in the background."
    }
    ```

    ### 3. Check Indexing Status
    **GET** `/status/{index_id}`
    **Response:**
    ```json
    {
    "index_id": "uuid",
    "status": "started | completed | failed",
    "repo_url": "...",
    "branch": "...",
    "error": "optional error message"
    }
    ```

    ### 4. Semantic Search
    **POST** `/search`
    ```json
    {
    "query": "how is authentication handled?",
    "repo": "my-repo",
    "branch": "main"
    }
    ```

    ### 5. RAG Execute
    **POST** `/execute`
    ```json
    {
    "tenant": "demo",
    "repo": "repo",
    "instruction": "Explain the login flow",
    "context_query": "authentication and user login",
    "constraints": { "json": true }
    }
    ```

    ## 📂 Project Structure
    - `api/`: REST API endpoints and request models.
    - `llm/`: Unified LLM drivers and provider factory.
    - `cocoindex_app/`: AST-aware indexing flows and hybrid search logic.
    - `memory_service/`: Multi-storage backends (FAISS, MongoDB, Postgres).
    - `foundation/`: Core reasoning engine and prompt templates.
    - `indexing/`: Git operations and file management.
