import os
import faiss
import numpy as np
import pickle

class FAISSStore:
    def __init__(self):
        self.index_path = os.environ.get("FAISS_INDEX_PATH", "./data/faiss_index")
        self.dimension = 384 # MiniLM-L6 dimension
        self.index = None
        self.metadata = [] # List of dicts to store text and other fields
        
        if os.path.exists(self.index_path):
            self.load()
        else:
            self.index = faiss.IndexFlatIP(self.dimension) # Inner Product == Cosine Similarity for normalized vectors

    def add(self, embeddings: np.ndarray, metadata: list):
        # Ensure embeddings are normalized for cosine similarity if using IndexFlatIP
        faiss.normalize_L2(embeddings)
        self.index.add(embeddings)
        self.metadata.extend(metadata)

    def search(self, query_vector: np.ndarray, k: int = 5):
        if self.index.ntotal == 0:
            return []
        
        faiss.normalize_L2(query_vector.reshape(1, -1))
        distances, indices = self.index.search(query_vector.reshape(1, -1), k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx == -1: continue
            res = self.metadata[idx].copy()
            res["score"] = float(distances[0][i])
            results.append(res)
        return results

    def save(self):
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        faiss.write_index(self.index, self.index_path + ".index")
        with open(self.index_path + ".meta", "wb") as f:
            pickle.dump(self.metadata, f)

    def load(self):
        if os.path.exists(self.index_path + ".index"):
            self.index = faiss.read_index(self.index_path + ".index")
            with open(self.index_path + ".meta", "rb") as f:
                self.metadata = pickle.load(f)
        else:
            self.index = faiss.IndexFlatIP(self.dimension)
            self.metadata = []

    def reset(self):
        self.index = faiss.IndexFlatIP(self.dimension)
        self.metadata = []
        if os.path.exists(self.index_path + ".index"):
            os.remove(self.index_path + ".index")
        if os.path.exists(self.index_path + ".meta"):
            os.remove(self.index_path + ".meta")
