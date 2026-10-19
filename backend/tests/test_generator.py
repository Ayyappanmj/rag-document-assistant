import httpx
import pytest

from app.config import Settings
from app.rag.generator import (
    Generator, LLMError, OllamaClient, OpenAICompatibleClient, create_llm_client,
)
from app.rag.prompt import NO_ANSWER, build_messages, is_refusal

MESSAGES = [{"role": "user", "content": "hi"}]


def mock(handler):
    return httpx.MockTransport(handler)


def test_prompt_contains_rules_context_and_question():
    msgs = build_messages("What was revenue?", "[Source 1] a.pdf, Page 1\nRevenue was 5.")
    assert msgs[0]["role"] == "system"
    assert "ONLY the provided context" in msgs[0]["content"]
    assert NO_ANSWER in msgs[0]["content"]
    assert "[Source 1] a.pdf, Page 1" in msgs[1]["content"]
    assert "What was revenue?" in msgs[1]["content"]


def test_is_refusal():
    assert is_refusal("I couldn't find enough information in the uploaded documents.")
    assert is_refusal("I couldn\u2019t find sufficient evidence in the uploaded documents.")
    assert not is_refusal("Revenue was 5 [Source 1].")


def test_ollama_success_and_request_shape():
    seen = {}

    def handler(request):
        seen["url"], seen["body"] = str(request.url), request.read()
        return httpx.Response(200, json={"message": {"content": " Hello "}})

    client = OllamaClient("http://localhost:11434/", "llama3.2", transport=mock(handler))
    assert client.complete(MESSAGES) == " Hello "
    assert seen["url"] == "http://localhost:11434/api/chat"
    assert b'"stream":false' in seen["body"].replace(b" ", b"")


def test_ollama_model_not_found_is_llm_error():
    client = OllamaClient("http://x", "nope", transport=mock(lambda r: httpx.Response(404, json={"error": "no"})))
    with pytest.raises(LLMError, match="404"):
        client.complete(MESSAGES)


def test_connection_error_is_llm_error():
    def handler(request):
        raise httpx.ConnectError("refused")

    with pytest.raises(LLMError, match="Could not reach"):
        OllamaClient("http://x", "m", transport=mock(handler)).complete(MESSAGES)


def test_timeout_is_llm_error():
    def handler(request):
        raise httpx.ReadTimeout("slow")

    with pytest.raises(LLMError, match="too long"):
        OllamaClient("http://x", "m", transport=mock(handler)).complete(MESSAGES)


def test_malformed_response_is_llm_error():
    client = OllamaClient("http://x", "m", transport=mock(lambda r: httpx.Response(200, json={"oops": 1})))
    with pytest.raises(LLMError):
        client.complete(MESSAGES)


def test_openai_compatible_sends_bearer_token_and_parses():
    seen = {}

    def handler(request):
        seen["auth"], seen["url"] = request.headers.get("authorization"), str(request.url)
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    client = OpenAICompatibleClient("https://api.example.com/v1", "gpt", api_key="secret", transport=mock(handler))
    assert client.complete(MESSAGES) == "ok"
    assert seen["auth"] == "Bearer secret"
    assert seen["url"] == "https://api.example.com/v1/chat/completions"


def test_openai_compatible_without_key_sends_no_auth_header():
    seen = {}

    def handler(request):
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    OpenAICompatibleClient("http://localhost:1234/v1", "m", transport=mock(handler)).complete(MESSAGES)
    assert seen["auth"] is None


def test_provider_selection():
    assert isinstance(create_llm_client(Settings(llm_provider="ollama")), OllamaClient)
    assert isinstance(create_llm_client(Settings(llm_provider="OpenAI")), OpenAICompatibleClient)
    with pytest.raises(ValueError):
        create_llm_client(Settings(llm_provider="skynet"))


def test_generator_strips_and_rejects_empty():
    class Fake:
        def __init__(self, out):
            self.out = out

        def complete(self, messages):
            return self.out

    assert Generator(Fake("  answer \n")).generate("q", "c") == "answer"
    with pytest.raises(LLMError):
        Generator(Fake("   ")).generate("q", "c")
