"""Central configuration via pydantic-settings (loads from .env or environment variables)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Azure OpenAI
    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_deployment_name: str = "gpt-4o"
    azure_openai_embedding_deployment: str = "text-embedding-3-small"

    # Azure AI Search
    azure_search_service_endpoint: str
    azure_search_admin_key: str
    azure_search_index_name: str = "obsidian-notes"

    # Azure Storage
    azure_storage_connection_string: str
    azure_storage_container_name: str = "obsidian-vault"

    # Local path (ingestion only)
    obsidian_vault_path: str = ""


settings = Settings()  # type: ignore[call-arg]
