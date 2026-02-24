"""
Phase 2 – Vector Index: Create embeddings from your notes and store them in Azure AI Search.

Usage:
    python -m src.ingestion.build_index

What this script does:
  1. Fetches all blobs from Azure Blob Storage.
  2. Splits long notes into smaller chunks (for better retrieval).
  3. Generates embeddings via Azure OpenAI (text-embedding-3-small).
  4. Indexes the chunks with vectors in Azure AI Search.
"""

import base64
import logging
import time

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
    SearchableField,
    VectorSearch,
    VectorSearchProfile,
)
from azure.storage.blob import BlobServiceClient
from openai import AzureOpenAI

from src.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CHUNK_SIZE = 1000      # Characters per chunk
CHUNK_OVERLAP = 100    # Overlap to preserve context between chunks


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Splits text into overlapping chunks."""
    chunks, start = [], 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def ensure_index(index_client: SearchIndexClient) -> None:
    """Creates the Azure AI Search index if it does not exist yet."""
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="title", type=SearchFieldDataType.String),
        SearchableField(name="content", type=SearchFieldDataType.String),
        SimpleField(name="tags", type=SearchFieldDataType.String),
        SimpleField(name="source_path", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="chunk_index", type=SearchFieldDataType.Int32),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=1536,
            vector_search_profile_name="hnsw-profile",
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="hnsw-algo")],
        profiles=[VectorSearchProfile(name="hnsw-profile", algorithm_configuration_name="hnsw-algo")],
    )

    index = SearchIndex(
        name=settings.azure_search_index_name,
        fields=fields,
        vector_search=vector_search,
    )

    existing = [i.name for i in index_client.list_indexes()]
    if settings.azure_search_index_name not in existing:
        index_client.create_index(index)
        logger.info("Index created: %s", settings.azure_search_index_name)
    else:
        logger.info("Index already exists: %s", settings.azure_search_index_name)


def get_embedding(openai_client: AzureOpenAI, text: str) -> list[float]:
    """Calls Azure OpenAI to generate an embedding vector."""
    response = openai_client.embeddings.create(
        model=settings.azure_openai_embedding_deployment,
        input=text,
    )
    return response.data[0].embedding


def run() -> None:
    blob_service = BlobServiceClient.from_connection_string(settings.azure_storage_connection_string)
    container = blob_service.get_container_client(settings.azure_storage_container_name)

    credential = AzureKeyCredential(settings.azure_search_admin_key)
    index_client = SearchIndexClient(settings.azure_search_service_endpoint, credential)
    search_client = SearchClient(
        settings.azure_search_service_endpoint,
        settings.azure_search_index_name,
        credential,
    )
    openai_client = AzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version="2024-02-01",
    )

    ensure_index(index_client)

    blobs = list(container.list_blobs())
    logger.info("Blobs to index: %d", len(blobs))

    batch: list[dict] = []
    for blob in blobs:
        blob_client = container.get_blob_client(blob.name)
        content = blob_client.download_blob().readall().decode("utf-8")
        metadata = blob.metadata or {}
        title = metadata.get("title", blob.name)
        tags = metadata.get("tags", "")

        for i, chunk in enumerate(chunk_text(content)):
            raw_id = f"{blob.name.replace('.md', '')}_{i}"
            doc_id = base64.urlsafe_b64encode(raw_id.encode()).decode()
            vector = get_embedding(openai_client, chunk)
            batch.append({
                "id": doc_id,
                "title": title,
                "content": chunk,
                "tags": tags,
                "source_path": blob.name,
                "chunk_index": i,
                "content_vector": vector,
            })

            # Upload in batches of 100 for efficiency
            if len(batch) >= 100:
                search_client.upload_documents(batch)
                logger.info("Indexed batch of %d documents.", len(batch))
                batch.clear()
                time.sleep(0.5)  # Brief pause to respect rate limits

    if batch:
        search_client.upload_documents(batch)
        logger.info("Indexed final batch of %d documents.", len(batch))

    logger.info("Indexing complete.")


if __name__ == "__main__":
    run()
