from typing import Any, Dict, List, Optional
from openai import OpenAI

def embedder(client: OpenAI, texts: List[str]) -> List[List[float]]:
    res = client.embeddings.create(model="text-embedding-3-small", input=texts)
    return [e.embedding for e in res.data]
