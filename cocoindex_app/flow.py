import os
import re
import cocoindex
from numpy.typing import NDArray
import numpy as np

# -------------------------------
# Shared transforms
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

@cocoindex.op.function()
def extract_symbols(code: str, language: str) -> list[str]:
    """Simple regex-based symbol extraction for AST hybrid flow."""
    patterns = {
        "python": [r"^(?:class|def)\s+([a-zA-Z_][a-zA-Z0-9_]*)"],
        "javascript": [r"(?:class|function)\s+([a-zA-Z_][a-zA-Z0-9_]*)", r"(?:const|let|var)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*="],
        "typescript": [r"(?:class|function|interface|type|enum)\s+([a-zA-Z_][a-zA-Z0-9_]*)"],
        "rust": [r"(?:fn|struct|enum|trait|type|mod)\s+([a-zA-Z_][a-zA-Z0-9_]*)"],
        "go": [r"(?:func|type|struct|interface)\s+([a-zA-Z_][a-zA-Z0-9_]*)"],
        "java": [r"(?:class|interface|enum|@interface)\s+([a-zA-Z_][a-zA-Z0-9_]*)"],
        "cpp": [r"(?:class|struct|enum|namespace)\s+([a-zA-Z_][a-zA-Z0-9_]*)"],
    }
    
    symbols = set()
    lang_lower = str(language).lower() if language else ""
    # Normalize language names
    if "python" in lang_lower: l_key = "python"
    elif "javascript" in lang_lower: l_key = "javascript"
    elif "typescript" in lang_lower: l_key = "typescript"
    elif "rust" in lang_lower: l_key = "rust"
    elif "go" in lang_lower: l_key = "go"
    elif "java" in lang_lower: l_key = "java"
    elif "c++" in lang_lower or "cpp" in lang_lower: l_key = "cpp"
    else: l_key = None

    if l_key and l_key in patterns:
        for pattern in patterns[l_key]:
            matches = re.findall(pattern, code, re.MULTILINE)
            symbols.update(matches)
    
    return sorted(list(symbols))

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
        pass

    scope["files"] = flow.add_source(
        cocoindex.sources.LocalFile(
            path=os.environ.get("CODEBASE_PATH", "/tmp/placeholder"), 
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
            # Extract symbols for this chunk
            c["symbols"] = c["text"].transform(extract_symbols, language=f["language"])

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
                symbols=c["symbols"],
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
