import os
import functools
import cocoindex
from psycopg_pool import ConnectionPool
from pgvector.psycopg import register_vector

from cocoindex_app.flow import code_index_flow, code_to_embedding

TOP_K = 50

@functools.cache
def pool() -> ConnectionPool:
    return ConnectionPool(os.environ["COCOINDEX_DATABASE_URL"])


@code_index_flow.query_handler(
    result_fields=cocoindex.QueryHandlerResultFields(
        embedding=["embedding"],
        score="score",
    )
)
async def search(
    query: str,
    repo: str | None = None,
    branch: str | None = None,
) -> cocoindex.QueryOutput:

    query_vector = await code_to_embedding.eval_async(query)
    backend = os.environ.get("STORAGE_BACKEND", "postgres")

    if backend == "faiss_mongo":
        from memory_service.faiss_store import FAISSStore
        faiss_store = FAISSStore()
        # FAISS search
        raw_results = faiss_store.search(query_vector, k=TOP_K)
        # Filter by repo/branch if provided
        if repo or branch:
            raw_results = [
                r for r in raw_results 
                if (not repo or r.get("repo") == repo) and (not branch or r.get("branch") == branch)
            ]
        
        # Convert to common format for reranking
        rows = []
        for r in raw_results:
            rows.append((
                r["filename"], r["language"], r["code"], r["start"], r["end"], 
                r["symbols"], r["calls"], 1.0 - r["score"] # Score to distance
            ))
    elif backend == "lancedb":
        import lancedb
        uri = os.environ.get("LANCEDB_URI", "./data/lancedb")
        # Ensure directory exists to avoid error if empty
        os.makedirs(uri, exist_ok=True)
        
        db = await lancedb.connect_async(uri)
        try:
            tbl = await db.open_table("code_embeddings")
            
            query_builder = tbl.vector_search(query_vector).limit(TOP_K)
            
            conditions = []
            if repo:
                # Escape quotes if necessary, simple implementation for now
                conditions.append(f"repo = '{repo}'")
            if branch:
                conditions.append(f"branch = '{branch}'")
                
            if conditions:
                query_builder = query_builder.where(" AND ".join(conditions))
            
            df = await query_builder.to_pandas()
            
            rows = []
            if not df.empty:
                for _, r in df.iterrows():
                    # LanceDB returns _distance
                    dist = r.get("_distance", 1.0)
                    rows.append((
                        r["filename"], r["language"], r["code"], r["start"], r["end"],
                        r["symbols"].tolist() if hasattr(r["symbols"], "tolist") else r["symbols"],
                        r["calls"].tolist() if hasattr(r["calls"], "tolist") else r["calls"],
                        dist
                    ))
        except Exception as e:
            print(f"LanceDB search failed (maybe table doesn't exist?): {e}")
            rows = []

    else:
        # Postgres Search
        table_name = cocoindex.utils.get_target_default_name(
            code_index_flow, "code_embeddings"
        )
        where = []
        params = [query_vector]
        if repo:
            where.append("\"repo\" = %s")
            params.append(repo)
        if branch:
            where.append("\"branch\" = %s")
            params.append(branch)

        where_sql = f"WHERE {' AND '.join(where)}" if where else ""
        sql = f"""
            SELECT "filename", "language", "code", "start", "end", "symbols", "calls", "embedding" <=> %s AS distance
            FROM {table_name} {where_sql} ORDER BY distance LIMIT %s
        """
        params.append(TOP_K)
        with pool().connection() as conn:
            register_vector(conn)
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()

    results = []
    query_terms = set(query.lower().split())

    for r in rows:
        filename, lang, code, start, end, symbols, calls, dist = r
        score = 1.0 - dist
        
        structural_match = False
        if symbols:
            if any(term in [s.lower() for s in symbols] for term in query_terms):
                score += 0.1
                structural_match = True
        if calls:
             if any(term in [c.lower() for c in calls] for term in query_terms):
                score += 0.05
                structural_match = True
        
        results.append({
            "filename": filename,
            "language": lang,
            "code": code,
            "start": start,
            "end": end,
            "symbols": symbols,
            "calls": calls,
            "score": score,
            "structural_boost": structural_match
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return cocoindex.QueryOutput(
        query_info=cocoindex.QueryInfo(
            embedding=query_vector,
            similarity_metric=cocoindex.VectorSimilarityMetric.COSINE_SIMILARITY,
        ),
        results=results[:TOP_K],
    )

@code_index_flow.query_handler()
async def get_all_embeddings():
    """Returns all indexed data from the master Postgres storage."""
    with pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT embedding, filename, location, start_line, end_line, code, symbols, calls, repo, branch FROM code_embeddings")
            results = []
            for row in cur.fetchall():
                results.append({
                    "embedding": row[0],
                    "filename": row[1],
                    "location": row[2],
                    "start": row[3],
                    "end": row[4],
                    "text": row[5],
                    "symbols": row[6],
                    "calls": row[7],
                    "repo": row[8],
                    "branch": row[9]
                })
            return cocoindex.query_handler.QueryOutput(results=results)
