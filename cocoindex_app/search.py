import os
import functools
import cocoindex
from psycopg_pool import ConnectionPool
from pgvector.psycopg import register_vector

from cocoindex_app.flow import code_index_flow, code_to_embedding

TOP_K = 25

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

    table_name = cocoindex.utils.get_target_default_name(
        code_index_flow, "code_embeddings"
    )

    query_vector = await code_to_embedding.eval_async(query)

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
        SELECT
            "filename",
            "language",
            "code",
            "start",
            "end",
            "symbols",
            "calls",
            "embedding" <=> %s AS distance
        FROM {table_name}
        {where_sql}
        ORDER BY distance
        LIMIT %s
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
        
        # Hybrid Reranking Logic: 
        # Boost if query terms exactly match definitions (symbols) or calls
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

    # Sort again after boosting
    results.sort(key=lambda x: x["score"], reverse=True)

    return cocoindex.QueryOutput(
        query_info=cocoindex.QueryInfo(
            embedding=query_vector,
            similarity_metric=cocoindex.VectorSimilarityMetric.COSINE_SIMILARITY,
        ),
        results=results[:TOP_K],
    )
