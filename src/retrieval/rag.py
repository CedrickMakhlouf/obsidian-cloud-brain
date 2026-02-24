"""
Phase 3 – RAG Retrieval: Fetches relevant notes from Azure AI Search
and answers questions via GPT-4o on Azure.
"""

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from openai import AzureOpenAI

from src.config import settings

SYSTEM_PROMPT = """You are a smart knowledge assistant that answers questions based on
the user's personal notes. Use ONLY the provided context.
If the answer is not in the context, say so honestly.
Always respond in the same language as the question.
"""

# ── Clients (éénmalig aangemaakt bij import) ───────────────────────────────────
_search_client = SearchClient(
    settings.azure_search_service_endpoint,
    settings.azure_search_index_name,
    AzureKeyCredential(settings.azure_search_admin_key),
)
_openai_client = AzureOpenAI(
    azure_endpoint=settings.azure_openai_endpoint,
    api_key=settings.azure_openai_api_key,
    api_version="2024-02-01",
)


def retrieve_context(query: str, top_k: int = 5) -> list[dict]:
    """
    Performs a hybrid search (vector + keyword) in Azure AI Search.
    Returns a list of relevant chunks.
    """

    # Generate query vector
    embedding_response = _openai_client.embeddings.create(
        model=settings.azure_openai_embedding_deployment,
        input=query,
    )
    query_vector = embedding_response.data[0].embedding

    vector_query = VectorizedQuery(
        vector=query_vector,
        k_nearest_neighbors=top_k,
        fields="content_vector",
    )

    results = _search_client.search(
        search_text=query,              # Keyword component
        vector_queries=[vector_query],   # Vector component
        select=["title", "content", "tags", "source_path"],
        top=top_k,
    )

    return [
        {
            "title": r["title"],
            "content": r["content"],
            "tags": r.get("tags", ""),
            "source_path": r["source_path"],
        }
        for r in results
    ]


def ask(question: str, top_k: int = 5) -> dict:
    """
    Core function of the RAG pipeline:
    1. Fetch relevant context from Azure AI Search.
    2. Send question + context to GPT-4o.
    3. Return answer + sources.
    """
    context_docs = retrieve_context(question, top_k=top_k)

    if not context_docs:
        return {
            "answer": "Geen relevante notities gevonden om de vraag te beantwoorden.",
            "sources": [],
        }

    context_text = "\n\n---\n\n".join(
        f"**{doc['title']}**\n{doc['content']}" for doc in context_docs
    )

    response = _openai_client.chat.completions.create(
        model=settings.azure_openai_deployment_name,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Context from my notes:\n\n{context_text}\n\nQuestion: {question}",
            },
        ],
        temperature=0.3,
        max_tokens=1000,
    )

    return {
        "answer": response.choices[0].message.content,
        "sources": [
            {"title": doc["title"], "path": doc["source_path"]} for doc in context_docs
        ],
    }
