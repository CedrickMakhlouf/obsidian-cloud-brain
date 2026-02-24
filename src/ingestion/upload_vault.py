"""
Phase 1 – Data Pipeline: Upload Obsidian Vault to Azure Blob Storage.

Usage:
    python -m src.ingestion.upload_vault

What this script does:
  1. Recursively scans the local Obsidian vault for all .md files.
  2. Parses YAML frontmatter and extracts tags/metadata.
  3. Uploads each file including metadata properties to Azure Blob Storage.
"""

import hashlib
import logging
from pathlib import Path

import frontmatter
from azure.storage.blob import BlobServiceClient, ContentSettings

from src.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def compute_md5(content: str) -> str:
    """Returns an MD5 hash of the text (for deduplication)."""
    return hashlib.md5(content.encode("utf-8")).hexdigest()


def parse_note(path: Path) -> dict:
    """
    Loads a Markdown file and extracts:
    - title: filename without extension
    - tags: list of tags from frontmatter
    - content: raw Markdown text
    - metadata: remaining frontmatter fields as a JSON string
    """
    post = frontmatter.load(str(path), encoding="utf-8")
    tags = post.metadata.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",")]
    elif not isinstance(tags, list):
        tags = [str(tags)] if tags else []
    # Ensure every tag element is a string
    tags = [str(t).strip() for t in tags if t is not None]

    return {
        "title": path.stem,
        "relative_path": str(path.relative_to(settings.obsidian_vault_path)),
        "tags": tags,
        "content": post.content,
        "raw_metadata": str(post.metadata),
        "md5": compute_md5(post.content),
    }


def _ascii_safe(value: str) -> str:
    """Strips non-ASCII characters (e.g. emoji) from Azure blob metadata."""
    return value.encode("ascii", errors="ignore").decode("ascii")


def upload_note(client: BlobServiceClient, note: dict) -> None:
    """Uploads a single Obsidian note as a blob with metadata."""
    blob_name = note["relative_path"].replace("\\", "/")
    blob_client = client.get_blob_client(
        container=settings.azure_storage_container_name,
        blob=blob_name,
    )

    blob_client.upload_blob(
        data=note["content"].encode("utf-8"),
        overwrite=True,
        content_settings=ContentSettings(content_type="text/markdown"),
        metadata={
            "title": _ascii_safe(note["title"]),
            "tags": _ascii_safe(",".join(note["tags"])),
            "md5": note["md5"],
        },
    )
    logger.info("Uploaded: %s", blob_name)


def run() -> None:
    vault = Path(settings.obsidian_vault_path)
    if not vault.exists():
        raise FileNotFoundError(f"Vault directory not found: {vault}")

    md_files = list(vault.rglob("*.md"))
    logger.info("Found %d .md files", len(md_files))

    service_client = BlobServiceClient.from_connection_string(
        settings.azure_storage_connection_string
    )

    # Create container if it does not exist yet
    container_client = service_client.get_container_client(
        settings.azure_storage_container_name
    )
    if not container_client.exists():
        container_client.create_container()
        logger.info("Container created: %s", settings.azure_storage_container_name)

    success, failed = 0, 0
    for path in md_files:
        try:
            note = parse_note(path)
            upload_note(service_client, note)
            success += 1
        except Exception as exc:
            logger.error("Failed for %s: %s", path, exc)
            failed += 1

    logger.info("Done. Succeeded: %d | Failed: %d", success, failed)


if __name__ == "__main__":
    run()
