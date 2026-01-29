# -*- coding: utf-8 -*-
"""
OpenAIProvider - OpenAI API compatible implementation.

This provider wraps the openai SDK to provide image-based content generation.
Supports OpenAI-compatible services (Azure, DeepSeek, Kimi, Together AI, etc.)
via the base_url parameter.
"""
import base64
import json
import mimetypes
from pathlib import Path
from typing import Any, Dict, List, Type, TypeVar

from loguru import logger
from openai import AsyncOpenAI
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_fixed

ResponseT = TypeVar("ResponseT", bound=BaseModel)


def extract_json_from_text(text: str) -> dict | None:
    """
    Extract JSON from text using multiple strategies.
    
    Strategies (in order):
    1. Extract from ```json ... ``` code block
    2. Extract from ``` ... ``` code block (no language tag)
    3. Find JSON object pattern { ... } in text
    """
    import re
    
    # Strategy 1: Extract from ```json ... ``` code block
    json_block_pattern = r"```json\s*([\s\S]*?)```"
    matches = re.findall(json_block_pattern, text)
    if matches:
        try:
            return json.loads(matches[0].strip())
        except json.JSONDecodeError:
            pass
    
    # Strategy 2: Extract from ``` ... ``` code block (no language tag)
    code_block_pattern = r"```\s*([\s\S]*?)```"
    matches = re.findall(code_block_pattern, text)
    if matches:
        try:
            return json.loads(matches[0].strip())
        except json.JSONDecodeError:
            pass
    
    # Strategy 3: Find JSON object pattern { ... } in text
    # Match the outermost { ... } pair
    json_object_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    matches = re.findall(json_object_pattern, text)
    if matches:
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
    
    return None


def _encode_image_to_base64(image_path: Path) -> str:
    """Encode an image file to base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def _get_mime_type(image_path: Path) -> str:
    """Get MIME type for an image file."""
    mime_type, _ = mimetypes.guess_type(str(image_path))
    return mime_type or "image/png"


def _pydantic_to_json_schema(model: Type[BaseModel]) -> Dict[str, Any]:
    """Convert Pydantic model to JSON Schema for OpenAI structured output."""
    schema = model.model_json_schema()

    # OpenAI requires additionalProperties: false for strict mode
    def add_additional_properties_false(obj: Dict[str, Any]) -> Dict[str, Any]:
        if isinstance(obj, dict):
            if obj.get("type") == "object":
                obj["additionalProperties"] = False
            for value in obj.values():
                if isinstance(value, dict):
                    add_additional_properties_false(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            add_additional_properties_false(item)
        return obj

    return add_additional_properties_false(schema)


class OpenAIProvider:
    """
    OpenAI-compatible chat provider implementation.

    This class encapsulates OpenAI API logic and supports any OpenAI-compatible
    service through the base_url parameter.

    Supported services:
    - OpenAI (default)
    - Azure OpenAI
    - DeepSeek
    - Kimi (Moonshot)
    - Together AI
    - Any OpenAI-compatible API
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
    ):
        """
        Initialize the OpenAI provider.

        Args:
            api_key: API key for the service.
            model: Model name to use (e.g., "gpt-4o", "deepseek-chat").
            base_url: Optional base URL for OpenAI-compatible services.
                      Examples:
                        - DeepSeek: "https://api.deepseek.com/v1"
                        - Kimi: "https://api.moonshot.cn/v1"
                        - Together: "https://api.together.xyz/v1"
        """
        self._api_key = api_key
        self._model = model
        self._base_url = base_url
        self._client: AsyncOpenAI | None = None
        self._response: Dict[str, Any] | None = None

    @property
    def client(self) -> AsyncOpenAI:
        """Lazy-initialize the OpenAI async client."""
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
            )
        return self._client

    @property
    def last_response(self) -> Dict[str, Any] | None:
        """Get the last response for debugging/caching purposes."""
        return self._response

    def _build_image_content(self, images: List[Path]) -> List[Dict[str, Any]]:
        """Build image content parts for the API request."""
        content_parts = []
        for image_path in images:
            if image_path and image_path.exists():
                base64_image = _encode_image_to_base64(image_path)
                mime_type = _get_mime_type(image_path)
                content_parts.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_image}",
                            "detail": "high",
                        },
                    }
                )
        return content_parts

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(3),
        before_sleep=lambda retry_state: logger.warning(
            f"Retry request ({retry_state.attempt_number}/3) - "
            f"Wait 3 seconds - Exception: {retry_state.outcome.exception()}"
        ),
    )
    async def generate_with_images(
        self,
        *,
        images: List[Path],
        response_schema: Type[ResponseT],
        user_prompt: str | None = None,
        description: str | None = None,
        **kwargs,
    ) -> ResponseT:
        """
        Generate content with image inputs.

        Args:
            images: List of image file paths to include in the request.
            response_schema: Pydantic model class for structured output.
            user_prompt: User-provided prompt/instructions.
            description: System instruction/description for the model.
            **kwargs: Additional options passed to the API.

        Returns:
            Parsed response matching the response_schema type.
        """
        # Build message content with images
        content_parts: List[Dict[str, Any]] = self._build_image_content(images)

        # Add user prompt if provided
        if user_prompt and isinstance(user_prompt, str):
            content_parts.append({"type": "text", "text": user_prompt})

        # Build messages
        messages: List[Dict[str, Any]] = []
        if description:
            messages.append({"role": "system", "content": description})
        messages.append({"role": "user", "content": content_parts})

        # Build response format for structured output
        json_schema = _pydantic_to_json_schema(response_schema)
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": response_schema.__name__,
                "schema": json_schema,
                "strict": True,
            },
        }

        # Make API request
        response = await self.client.chat.completions.create(
            model=self._model,
            messages=messages,
            response_format=response_format,
            **kwargs,
        )

        # Store response for caching
        self._response = response.model_dump(mode="json")

        # Extract content
        response_text = response.choices[0].message.content

        # Parse response
        if response_text:
            # First try direct JSON parsing (for providers that support structured output)
            try:
                json_data = json.loads(response_text.strip())
                return response_schema(**json_data)
            except json.JSONDecodeError:
                pass
            
            # Fallback: extract JSON from text (for providers without structured output)
            json_data = extract_json_from_text(response_text)
            if json_data:
                try:
                    return response_schema(**json_data)
                except Exception as e:
                    logger.warning(f"Failed to validate extracted JSON: {e}")

        raise ValueError(f"Failed to parse response: {response_text}")

    def cache_response(self, path: Path) -> None:
        """Cache the last response to a file."""
        if not self._response:
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(self._response, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning(f"Failed to cache response: {e}")

