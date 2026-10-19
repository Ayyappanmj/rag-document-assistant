"""LLM clients (Ollama by default, any OpenAI-compatible API optionally) and the Generator."""
import json
import logging
from collections.abc import Iterator
from typing import Protocol

import httpx

from app.config import Settings
from app.rag.prompt import build_messages

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Raised with a user-safe message when the LLM call fails."""


class LLMClient(Protocol):
    def complete(self, messages: list[dict]) -> str: ...
    def stream(self, messages: list[dict]) -> Iterator[str]: ...


def _post_json(url: str, payload: dict, headers: dict, timeout: float, transport=None) -> dict:
    try:
        with httpx.Client(timeout=timeout, transport=transport) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.ConnectError as exc:
        raise LLMError("Could not reach the language model server.") from exc
    except httpx.TimeoutException as exc:
        raise LLMError("The language model took too long to respond.") from exc
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        logger.error("llm_http_error status=%d", status)  # body is not logged: it may echo the prompt
        raise LLMError(f"The language model returned an error (HTTP {status}).") from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise LLMError("The language model returned an unexpected response.") from exc


class OllamaClient:
    def __init__(self, base_url: str, model: str, temperature: float = 0.1, timeout: float = 120.0, transport=None):
        self._url = f"{base_url.rstrip('/')}/api/chat"
        self._model, self._temperature, self._timeout, self._transport = model, temperature, timeout, transport

    def complete(self, messages: list[dict]) -> str:
        payload = {
            "model": self._model, "messages": messages, "stream": False,
            "options": {"temperature": self._temperature},
        }
        data = _post_json(self._url, payload, {}, self._timeout, self._transport)
        try:
            return data["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise LLMError("The language model returned an unexpected response.") from exc

    def stream(self, messages: list[dict]) -> Iterator[str]:
        payload = {
            "model": self._model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": self._temperature},
        }
        try:
            with httpx.Client(timeout=self._timeout, transport=self._transport) as client:
                with client.stream("POST", self._url, json=payload) as resp:
                    resp.raise_for_status()
                    for line in resp.iter_lines():
                        if not line.strip():
                            continue
                        data = json.loads(line)
                        chunk = data.get("message", {}).get("content", "")
                        if chunk:
                            yield chunk
        except httpx.ConnectError as exc:
            raise LLMError("Could not reach the language model server.") from exc
        except httpx.TimeoutException as exc:
            raise LLMError("The language model took too long to respond.") from exc
        except httpx.HTTPStatusError as exc:
            raise LLMError(f"The language model returned an error (HTTP {exc.response.status_code}).") from exc
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            raise LLMError("The language model returned an unexpected response.") from exc


class OpenAICompatibleClient:
    def __init__(self, base_url: str, model: str, api_key: str = "", temperature: float = 0.1,
                 timeout: float = 120.0, transport=None):
        self._url = f"{base_url.rstrip('/')}/chat/completions"
        self._model, self._api_key = model, api_key
        self._temperature, self._timeout, self._transport = temperature, timeout, transport

    def complete(self, messages: list[dict]) -> str:
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        payload = {"model": self._model, "messages": messages, "temperature": self._temperature}
        data = _post_json(self._url, payload, headers, self._timeout, self._transport)
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("The language model returned an unexpected response.") from exc

    def stream(self, messages: list[dict]) -> Iterator[str]:
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": self._temperature,
            "stream": True,
        }
        try:
            with httpx.Client(timeout=self._timeout, transport=self._transport) as client:
                with client.stream("POST", self._url, json=payload, headers=headers) as resp:
                    resp.raise_for_status()
                    for line in resp.iter_lines():
                        clean_line = line.strip()
                        if not clean_line:
                            continue
                        if clean_line.startswith("data: "):
                            data_str = clean_line[6:].strip()
                            if data_str == "[DONE]":
                                break
                            data = json.loads(data_str)
                            choices = data.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                chunk = delta.get("content", "")
                                if chunk:
                                    yield chunk
        except httpx.ConnectError as exc:
            raise LLMError("Could not reach the language model server.") from exc
        except httpx.TimeoutException as exc:
            raise LLMError("The language model took too long to respond.") from exc
        except httpx.HTTPStatusError as exc:
            raise LLMError(f"The language model returned an error (HTTP {exc.response.status_code}).") from exc
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            raise LLMError("The language model returned an unexpected response.") from exc


def create_llm_client(settings: Settings) -> LLMClient:
    provider = settings.llm_provider.lower()
    if provider == "ollama":
        return OllamaClient(settings.ollama_base_url, settings.ollama_model,
                            settings.llm_temperature, settings.llm_timeout_seconds)
    if provider == "openai":
        return OpenAICompatibleClient(settings.openai_base_url, settings.openai_model, settings.openai_api_key,
                                      settings.llm_temperature, settings.llm_timeout_seconds)
    raise ValueError(f"Unsupported LLM_PROVIDER: {settings.llm_provider!r} (use 'ollama' or 'openai')")


class Generator:
    def __init__(self, client: LLMClient):
        self._client = client

    def generate(self, question: str, context: str) -> str:
        answer = self._client.complete(build_messages(question, context)).strip()
        if not answer:
            raise LLMError("The language model returned an empty answer.")
        return answer

    def generate_stream(self, question: str, context: str) -> Iterator[str]:
        messages = build_messages(question, context)
        yielded = False
        for chunk in self._client.stream(messages):
            yielded = True
            yield chunk
        if not yielded:
            raise LLMError("The language model returned an empty answer.")
