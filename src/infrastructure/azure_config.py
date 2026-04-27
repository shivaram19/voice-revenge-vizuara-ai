"""
Azure-Specific Configuration Loader
Reads configuration from environment variables and Azure Key Vault.
Ref: Microsoft (2024). Azure Identity SDK. learn.microsoft.com/azure/developer/python/sdk/

Design: Managed Identity for AKS → Key Vault → Secrets.
Fallback: Environment variables for local dev.
"""

import os
from typing import Optional
from dataclasses import dataclass


@dataclass(frozen=True)
class AzureConfig:
    """Azure-specific runtime configuration."""

    # Azure OpenAI
    openai_endpoint: str
    openai_key: str
    openai_deployment: str
    openai_api_version: str

    # Azure Cache for Redis
    redis_host: str
    redis_key: str
    redis_port: int
    redis_ssl: bool

    # Azure AI Search
    search_endpoint: str
    search_key: str
    search_index_name: str

    # Azure Blob Storage
    storage_connection_string: str
    storage_container_recordings: str
    storage_container_faq: str

    # Twilio
    twilio_account_sid: str
    twilio_auth_token: str

    # Application Insights
    appinsights_connection_string: Optional[str]

    @classmethod
    def from_env(cls) -> "AzureConfig":
        """
        Load configuration from environment variables.
        Production: Values injected by External Secrets Operator from Key Vault.
        Local dev: Values set in .env file or shell.
        """
        return cls(
            openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            openai_key=os.getenv("AZURE_OPENAI_KEY", ""),
            openai_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
            openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-06-01"),
            redis_host=os.getenv("REDIS_HOST", "localhost"),
            redis_key=os.getenv("REDIS_KEY", ""),
            redis_port=int(os.getenv("REDIS_PORT", "6379")),
            redis_ssl=os.getenv("REDIS_SSL", "false").lower() == "true",
            search_endpoint=os.getenv("SEARCH_ENDPOINT", ""),
            search_key=os.getenv("SEARCH_KEY", ""),
            search_index_name=os.getenv("SEARCH_INDEX_NAME", "faq-knowledge-base"),
            storage_connection_string=os.getenv("STORAGE_CONNECTION_STRING", ""),
            storage_container_recordings=os.getenv("BLOB_CONTAINER_RECORDINGS", "recordings"),
            storage_container_faq=os.getenv("BLOB_CONTAINER_FAQ", "faq-documents"),
            twilio_account_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
            twilio_auth_token=os.getenv("TWILIO_AUTH_TOKEN", ""),
            appinsights_connection_string=os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"),
        )

    def validate(self) -> list[str]:
        """Return list of missing required configuration keys."""
        missing = []
        required = [
            ("openai_endpoint", self.openai_endpoint),
            ("openai_key", self.openai_key),
            ("redis_host", self.redis_host),
            ("twilio_account_sid", self.twilio_account_sid),
            ("twilio_auth_token", self.twilio_auth_token),
        ]
        for name, value in required:
            if not value:
                missing.append(name)
        return missing
