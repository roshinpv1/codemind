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
def search(
    query: str,
    repo: str | None = None,
    branch: str | None = None,
) -> cocoindex.QueryOutput:

    table_name = cocoindex.utils.get_target_default_name(
        code_index_flow, "code_embeddings"
    )

    query_vector = code_to_embedding.eval(query)

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

    return cocoindex.QueryOutput(
        query_info=cocoindex.QueryInfo(
            embedding=query_vector,
            similarity_metric=cocoindex.VectorSimilarityMetric.COSINE_SIMILARITY,
        ),
        results=[
            {
                "filename": r[0],
                "language": r[1],
                "code": r[2],
                "start": r[3],
                "end": r[4],
                "score": 1.0 - r[5],
            }
            for r in rows
        ],
    )
