import requests
from sentence_transformers import SentenceTransformer

# Singleton cache so model isn't reloaded every call
_local_model_cache = {}


class callm3e():
    """Calls a remote OpenAI-compatible embedding API (e.g., m3e-base served via vLLM/FastEmbed)."""

    def __init__(self, embapi) -> None:
        self.server = embapi['url']
        self.header = {
            "Content-Type": 'application/json',
            "Accept": 'application/json',
            "Authorization": 'Bearer ' + embapi['token']
        }
        self.modelname = embapi['name']

    def init_prompt(self, prompt):
        self.input = {
            "model": self.modelname,
            "input": prompt
        }
        return self

    def call(self):
        try:
            response = requests.post(
                url=self.server,
                json=self.input,
                headers=self.header,
                timeout=15
            ).json()
            vector = response['data'][0]['embedding']
        except Exception as e:
            print(f"[EMB] Remote embedding failed: {e}")
            vector = 'Emb Fail'
        return vector


def vectorize_localmodel(somestr, model_path="./m3e-base"):
    """
    Vectorize text using a local SentenceTransformer model.
    Falls back to 'all-MiniLM-L6-v2' (auto-downloaded) if m3e-base weights are not present.
    Uses in-process model caching to avoid repeated disk loads.
    """
    global _local_model_cache

    import os
    # Detect if m3e-base has real model files (more than just readme.md)
    model_files = os.listdir(model_path) if os.path.isdir(model_path) else []
    has_real_weights = any(f.endswith(('.bin', '.safetensors', '.pt')) for f in model_files)

    if has_real_weights:
        load_path = model_path
    else:
        print(f"[EMB] m3e-base weights not found at '{model_path}'. Falling back to 'all-MiniLM-L6-v2'.")
        load_path = "sentence-transformers/all-MiniLM-L6-v2"

    try:
        if load_path not in _local_model_cache:
            print(f"[EMB] Loading model: {load_path} ...")
            _local_model_cache[load_path] = SentenceTransformer(load_path)
            print(f"[EMB] Model loaded successfully.")

        model = _local_model_cache[load_path]
        vector = list(model.encode(somestr, normalize_embeddings=True).tolist())
        return vector

    except Exception as e:
        print(f"[EMB] Local embedding failed: {e}")
        return 'Emb Fail'


if __name__ == '__main__':
    res = vectorize_localmodel('hello world')
    if res != 'Emb Fail':
        print(f"Embedding OK. Vector length: {len(res)}, first 5 dims: {res[:5]}")
    else:
        print("Embedding FAILED")
