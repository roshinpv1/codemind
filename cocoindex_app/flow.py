import os
import cocoindex
from numpy.typing import NDArray
import numpy as np

# -------------------------------
# Shared embedding transform
# -------------------------------

@cocoindex.transform_flow()
def code_to_embedding(
    text: cocoindex.DataSlice[str],
) -> cocoindex.DataSlice[NDArray[np.float32]]:
    return text.transform(
        cocoindex.functions.SentenceTransformerEmbed(
            model="sentence-transformers/all-MiniLM-L6-v2"
        )
    )

# -------------------------------
# Indexing flow
# -------------------------------

@cocoindex.flow_def(name="RealtimeCodeIndex")
def code_index_flow(
    flow: cocoindex.FlowBuilder,
    scope: cocoindex.DataScope,
) -> None:
    
    codebase_path = os.environ.get("CODEBASE_PATH")
    if not codebase_path or not os.path.exists(codebase_path):
        # We might be in a state where codebase path is not yet set (e.g. startup)
        # However, the flow compilation requires valid source structure.
        # But for 'update', it will read env.
        pass

    scope["files"] = flow.add_source(
        cocoindex.sources.LocalFile(
            path=os.environ.get("CODEBASE_PATH", "/tmp/placeholder"), # Default to avoid compile error if env missing during import
            included_patterns=[
                "**/*.py", "**/*.md", "**/*.mdx", "**/*.rs", "**/*.toml",
                "**/*.js", "**/*.jsx", "**/*.ts", "**/*.tsx", 
                "**/*.java", "**/*.c", "**/*.cpp", "**/*.h", "**/*.hpp",
                "**/*.go", "**/*.rb", "**/*.php", "**/*.sh", 
                "**/*.yaml", "**/*.yml", "**/*.json", "**/*.sql"
            ],
            excluded_patterns=["**/.git/**", "**/node_modules/**", "**/__pycache__/**", "**/.*"],
        )
    )

    collector = scope.add_collector()

    with scope["files"].row() as f:
        # Detect language
        f["language"] = f["filename"].transform(
            cocoindex.functions.DetectProgrammingLanguage()
        )

        # Chunk content
        f["chunks"] = f["content"].transform(
            cocoindex.functions.SplitRecursively(),
            language=f["language"],
            chunk_size=1000,
            min_chunk_size=300,
            chunk_overlap=300,
        )

        with f["chunks"].row() as c:
            # Generate embedding
            c["embedding"] = c["text"].call(code_to_embedding)

            # Metadata from env
            repo_name = os.environ.get("REPO_NAME", "unknown")
            branch_name = os.environ.get("BRANCH_NAME", "unknown")
            index_id = os.environ.get("INDEX_RUN_ID", "unknown")

            collector.collect(
                filename=f["filename"],
                language=f["language"],
                location=c["location"],
                start=c["start"],
                end=c["end"],
                code=c["text"],
                embedding=c["embedding"],
                repo=repo_name,
                branch=branch_name,
                index_id=index_id,
            )

    collector.export(
        "code_embeddings",
        cocoindex.targets.Postgres(),
        primary_key_fields=["filename", "location"],
        vector_indexes=[
            cocoindex.VectorIndexDef(
                field_name="embedding",
                metric=cocoindex.VectorSimilarityMetric.COSINE_SIMILARITY,
            )
        ],
    )
