import os
import re
import cocoindex
from numpy.typing import NDArray
import numpy as np
from tree_sitter_languages import get_language, get_parser

# -------------------------------
# AST Extraction Logic
# -------------------------------

def get_ast_metadata(code: str, language_name: str):
    """
    Extracts definitions and calls from code using tree-sitter.
    """
    try:
        # Normalize language names for tree-sitter
        lang_map = {
            "python": "python",
            "javascript": "javascript",
            "typescript": "typescript",
            "rust": "rust",
            "go": "go",
            "java": "java",
            "cpp": "cpp",
            "c": "c",
        }
        
        l_key = None
        lang_lower = str(language_name).lower()
        for k, v in lang_map.items():
            if k in lang_lower:
                l_key = v
                break
        
        if not l_key:
            return {"symbols": [], "calls": []}

        parser = get_parser(l_key)
        tree = parser.parse(bytes(code, "utf8"))
        
        symbols = set()
        calls = set()
        
        # Simple queries for definitions across languages (best effort)
        # Note: In a real prod sys we'd use language-specific queries.
        # But this generic approach covers most 'name' identifiers in defs.
        
        def traverse(node):
            # Definitions check (very basic heuristic)
            if node.type in ["function_definition", "class_definition", "method_definition", "function_item", "struct_item", "trait_item"]:
                # Look for name child
                for child in node.children:
                    if "name" in child.type or child.type == "identifier":
                        symbols.add(code[child.start_byte:child.end_byte])
                        break
            
            # Calls check
            if node.type in ["call", "call_expression", "invocation", "function_call"]:
                # Look for the function name
                for child in node.children:
                    if child.type in ["identifier", "field_identifier", "member_expression"]:
                        calls.add(code[child.start_byte:child.end_byte])
                        break
                        
            for child in node.children:
                traverse(child)
                
        traverse(tree.root_node)
        return {"symbols": sorted(list(symbols)), "calls": sorted(list(calls))}
    except Exception as e:
        print(f"AST parsing failed for {language_name}: {e}")
        return {"symbols": [], "calls": []}

@cocoindex.op.function()
def extract_code_metadata(code: str, language: str) -> cocoindex.Json:
    """Uses tree-sitter to extract rich structural metadata."""
    return get_ast_metadata(code, language)

@cocoindex.op.function()
def get_symbols(meta: dict) -> list[str]:
    return meta.get("symbols", [])

@cocoindex.op.function()
def get_calls(meta: dict) -> list[str]:
    return meta.get("calls", [])

@cocoindex.transform_flow()
def code_to_embedding(
    text: cocoindex.DataSlice[str],
) -> cocoindex.DataSlice[NDArray[np.float32]]:
    return text.transform(
        cocoindex.functions.SentenceTransformerEmbed(
            model=os.environ.get("EMBEDDING_MODEL_PATH", "sentence-transformers/all-MiniLM-L6-v2")
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
            # Extract symbols and calls for this chunk
            c["meta"] = c["text"].transform(extract_code_metadata, language=f["language"])
            c["symbols"] = c["meta"].transform(get_symbols)
            c["calls"] = c["meta"].transform(get_calls)

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
                calls=c["calls"],
                repo=repo_name,
                branch=branch_name,
                index_id=index_id,
            )

    # Export to Storage (Postgres or LanceDB)
    storage_backend = os.environ.get("STORAGE_BACKEND", "postgres")
    
    if storage_backend == "lancedb":
        # Ensure imports are available
        import cocoindex.targets.lancedb as lancedb_target_module
        
        target = lancedb_target_module.LanceDB(
            db_uri=os.environ.get("LANCEDB_URI", "./data/lancedb"),
            table_name="code_embeddings"
        )
        # LanceDB handles vector indexing internally/automatically or via options, 
        # but we pass vector_indexes for metadata if supported.
        # Based on inspection, LanceDB target takes vector indices.
        
        collector.export(
            "code_embeddings",
            target,
            primary_key_fields=["filename", "location"],
            # vector_indexes=[
            #    cocoindex.VectorIndexDef(
            #        field_name="embedding",
            #        metric=cocoindex.VectorSimilarityMetric.COSINE_SIMILARITY,
            #    )
            # ],
        )
    else:
        # Default: Postgres
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

    # Query handlers are added to the code_index_flow object after definition
    # See cocoindex_app/search.py
