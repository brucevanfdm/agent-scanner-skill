# Copyright 2026 Cisco Systems, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

"""
LLM Provider Configuration Handler.

Handles detection and configuration of different LLM providers
(Anthropic, OpenAI, Azure, Bedrock, Gemini).
"""

import importlib.util
import os
from collections.abc import Mapping

# Check for Google GenAI availability
# Wrap in try/except because find_spec can fail in partially installed
# namespace package states.
try:
    GOOGLE_GENAI_AVAILABLE = importlib.util.find_spec("google.genai") is not None
except Exception:
    # find_spec can fail when namespace packages are partially/broken installed.
    GOOGLE_GENAI_AVAILABLE = False

# Check for LiteLLM availability
try:
    LITELLM_AVAILABLE = importlib.util.find_spec("litellm") is not None
except Exception:
    LITELLM_AVAILABLE = False


def _is_truthy(value: str | None) -> bool:
    """Interpret common env-var boolean values."""
    if value is None:
        return False
    return value.strip().lower() not in {"", "0", "false", "no", "off"}


def _detect_provider_family(model: str) -> str:
    """Infer provider family from model string."""
    model_lower = model.lower()

    if "bedrock/" in model or model_lower.startswith("bedrock/"):
        return "bedrock"
    if model_lower.startswith("vertex_ai/") or "vertex" in model_lower:
        return "vertex"
    if model_lower.startswith("ollama/"):
        return "ollama"
    if model_lower.startswith("openrouter/"):
        return "openrouter"
    if model_lower.startswith("azure/") or "azure" in model_lower:
        return "azure"
    if "gemini" in model_lower or model_lower.startswith("gemini/"):
        return "gemini"
    if "claude" in model_lower or "anthropic" in model_lower:
        return "anthropic"
    if (
        model_lower.startswith("gpt")
        or model_lower.startswith("o1")
        or model_lower.startswith("o3")
        or "openai" in model_lower
    ):
        return "openai"
    return "generic"


def resolve_llm_api_key(
    model: str,
    explicit_api_key: str | None = None,
    env: Mapping[str, str] | None = None,
) -> str | None:
    """Resolve API key/credentials path for a model.

    Resolution order:
    1) Explicit parameter
    2) SKILL_SCANNER_LLM_API_KEY
    3) Provider-specific env vars (enabled by default)

    Provider-specific fallback can be disabled with:
    `SKILL_SCANNER_ALLOW_PROVIDER_ENV_FALLBACK=0`.
    """
    if explicit_api_key is not None:
        return explicit_api_key

    env_map = os.environ if env is None else env
    provider = _detect_provider_family(model)

    if provider == "vertex":
        # Vertex AI typically uses ADC or service account credentials path.
        return env_map.get("GOOGLE_APPLICATION_CREDENTIALS")
    if provider == "ollama":
        # Local model server, API key is usually not required.
        return None

    if scanner_key := env_map.get("SKILL_SCANNER_LLM_API_KEY"):
        return scanner_key

    allow_provider_fallback = _is_truthy(env_map.get("SKILL_SCANNER_ALLOW_PROVIDER_ENV_FALLBACK", "1"))
    if not allow_provider_fallback:
        return None

    provider_env_candidates = {
        "anthropic": ["ANTHROPIC_API_KEY"],
        "openai": ["OPENAI_API_KEY"],
        "azure": ["AZURE_OPENAI_API_KEY", "OPENAI_API_KEY"],
        "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        "openrouter": ["OPENROUTER_API_KEY"],
        # Bedrock usually relies on IAM/instance credentials.
        "bedrock": [],
        "generic": ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY"],
    }

    for key_name in provider_env_candidates.get(provider, provider_env_candidates["generic"]):
        if value := env_map.get(key_name):
            return value

    return None


class ProviderConfig:
    """Handles LLM provider detection and configuration."""

    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
        api_version: str | None = None,
        aws_region: str | None = None,
        aws_profile: str | None = None,
        aws_session_token: str | None = None,
    ):
        """
        Initialize provider configuration.

        Args:
            model: Model identifier
            api_key: API key (if None, reads from environment)
            base_url: Custom base URL (for Azure)
            api_version: API version (for Azure)
            aws_region: AWS region (for Bedrock)
            aws_profile: AWS profile name (for Bedrock)
            aws_session_token: AWS session token (for Bedrock)
        """
        self.model = model
        self.base_url = base_url
        self.api_version = api_version
        self.aws_region = aws_region or os.getenv("AWS_REGION", "us-east-1")
        self.aws_profile = aws_profile or os.getenv("AWS_PROFILE")
        self.aws_session_token = aws_session_token or os.getenv("AWS_SESSION_TOKEN")

        # Detect provider type from model string
        model_lower = model.lower()
        self.is_bedrock = "bedrock/" in model or model_lower.startswith("bedrock/")
        self.is_gemini = "gemini" in model_lower or model_lower.startswith("gemini/")
        self.is_azure = model_lower.startswith("azure/") or "azure" in model_lower
        self.is_vertex = model_lower.startswith("vertex_ai/") or "vertex" in model_lower
        self.is_ollama = model_lower.startswith("ollama/")
        self.is_openrouter = model_lower.startswith("openrouter/")

        # Determine if we should use Google SDK
        self.use_google_sdk = False

        # Handle Vertex AI separately (uses LiteLLM, not Google SDK)
        if self.is_vertex:
            # Vertex AI models stay as-is for LiteLLM
            if not LITELLM_AVAILABLE:
                raise ImportError("LiteLLM is required for Vertex AI. Install with: pip install litellm")
            self.model = model  # Keep vertex_ai/ prefix for LiteLLM
        elif self.is_gemini and GOOGLE_GENAI_AVAILABLE:
            # Google AI Studio (uses Google SDK directly)
            self.use_google_sdk = True
            self.model = self._normalize_gemini_model_name(model)
        elif self.is_gemini and not GOOGLE_GENAI_AVAILABLE:
            raise ImportError(
                "For Gemini models, either LiteLLM or google-genai is required. "
                "Install with: pip install litellm or pip install google-genai"
            )
        elif not LITELLM_AVAILABLE:
            raise ImportError("LiteLLM is required for enhanced LLM analyzer. Install with: pip install litellm")
        else:
            # Normalize Gemini model name for LiteLLM (Google AI Studio via LiteLLM)
            if self.is_gemini and not model.startswith("gemini/"):
                model_name = model.replace("gemini-", "").replace("gemini/", "")
                self.model = f"gemini/{model_name}"
            else:
                self.model = model

        # Resolve API key
        self.api_key = self._resolve_api_key(api_key)

        # Note: Google SDK client is created per-request, not configured globally

    def _resolve_api_key(self, api_key: str | None) -> str | None:
        """Resolve API key from parameter or environment variables.

        Supports both scanner-specific env var and provider-native env vars.
        """
        return resolve_llm_api_key(model=self.model, explicit_api_key=api_key)

    def _normalize_gemini_model_name(self, model: str) -> str:
        """
        Normalize Gemini model name for Google GenAI SDK (new SDK).

        Handles various input formats:
        - gemini-1.5-pro -> models/gemini-1.5-pro (or models/gemini-pro-latest)
        - gemini-2.5-flash -> models/gemini-2.5-flash
        - gemini/2.0-flash -> models/gemini-2.0-flash
        - models/gemini-2.5-pro -> models/gemini-2.5-pro (already correct)

        Args:
            model: Input model name

        Returns:
            Normalized model name for Google SDK (with models/ prefix)
        """
        # Remove any "gemini/" prefix (LiteLLM format)
        model_name = model.replace("gemini/", "")

        # Remove models/ prefix if present (will add it back)
        model_name = model_name.replace("models/", "")

        # Map legacy model names to available models
        model_mapping = {
            "gemini-1.5-pro": "gemini-pro-latest",  # Map to latest available
            "gemini-1.5-flash": "gemini-flash-latest",  # Map to latest available
        }

        if model_name in model_mapping:
            model_name = model_mapping[model_name]

        # If it's just a version/variant, add "gemini-" prefix
        if not model_name.startswith("gemini-"):
            model_name = f"gemini-{model_name}"

        # Add models/ prefix for new SDK
        if not model_name.startswith("models/"):
            model_name = f"models/{model_name}"

        return model_name

    def validate(self) -> None:
        """Validate that configuration is complete."""
        # Keyless auth is supported for some providers (Bedrock IAM, Ollama local, Vertex ADC).
        if not self.is_bedrock and not self.is_ollama and not self.is_vertex and not self.api_key:
            raise ValueError(f"API key required for model {self.model}")

    def get_request_params(self) -> dict:
        """Get request parameters for LiteLLM."""
        params = {}

        if self.api_key:
            # Pass api_key per request. Avoid mutating global environment at runtime.
            params["api_key"] = self.api_key

        if self.base_url:
            params["api_base"] = self.base_url
        if self.api_version:
            params["api_version"] = self.api_version

        if self.is_bedrock:
            # AWS Bedrock supports:
            # 1. Bearer token auth via api_key (format: bedrock-api-key-*)
            # 2. IAM credentials via boto3 (falls back if no bearer token)
            if self.aws_region:
                params["aws_region_name"] = self.aws_region
            if self.aws_session_token:
                params["aws_session_token"] = self.aws_session_token
            if self.aws_profile:
                params["aws_profile_name"] = self.aws_profile

        return params
