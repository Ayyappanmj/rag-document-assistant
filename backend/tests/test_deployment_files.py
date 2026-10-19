"""Guards against the classic deployment mistakes: secrets in git or images, root containers, bloated images."""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(not (ROOT / "docker-compose.yml").exists(), reason="not a full checkout")


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_env_files_are_git_ignored_and_docker_ignored():
    assert ".env" in read(".gitignore").splitlines()
    assert ".env" in read(".dockerignore").splitlines()
    assert ".env" in read("frontend/.dockerignore").splitlines()


def test_no_real_secrets_in_example_or_compose():
    for name in (".env.example", "docker-compose.yml"):
        text = read(name)
        assert "sk-" not in text, f"{name} looks like it contains an API key"
    key_lines = [l for l in read(".env.example").splitlines() if l.strip().startswith("OPENAI_API_KEY")]
    assert all(l.strip().endswith("=") or l.startswith("#") for l in key_lines)


def test_backend_image_runs_as_non_root_and_uses_cpu_torch():
    dockerfile = read("backend/Dockerfile")
    assert "USER app" in dockerfile
    assert "download.pytorch.org/whl/cpu" in dockerfile
    assert "COPY .env" not in dockerfile and ".env" not in dockerfile.replace(".environment", "")


def test_frontend_image_runs_as_non_root_and_uses_standalone_output():
    dockerfile = read("frontend/Dockerfile")
    assert "USER nextjs" in dockerfile and "NEXT_OUTPUT=standalone" in dockerfile
    assert 'standalone' in read("frontend/next.config.ts")


def test_compose_persists_data_and_does_not_publish_secrets():
    compose = read("docker-compose.yml")
    for needle in ("rag_data:/app/data", "eval_data:/evaluation", "healthcheck:", "profiles:"):
        assert needle in compose
    assert "SECRET_KEY: ${SECRET_KEY:-change-this-secret}" in compose  # a default, never a real value


def test_runtime_requirements_do_not_include_test_tools():
    runtime = read("backend/requirements.txt").lower()
    assert "pytest" not in runtime
    dev = read("backend/requirements-dev.txt")
    assert "-r requirements.txt" in dev and "pytest" in dev


def test_every_env_example_setting_exists_in_the_backend_settings():
    from app.config import Settings

    fields = {name.upper() for name in Settings.model_fields}
    frontend_or_docker = {
        "NEXT_PUBLIC_API_URL", "NEXT_PUBLIC_GITHUB_URL", "BACKEND_URL", "DOCKER_OLLAMA_URL", "API_DOMAIN", "BACKEND_BIND", "INSTALL_CHROMA",
    }
    for line in read(".env.example").splitlines():
        line = line.strip().lstrip("#").strip()
        if "=" in line and line.split("=")[0].isupper() and " " not in line.split("=")[0]:
            key = line.split("=")[0]
            assert key in fields or key in frontend_or_docker, f"{key} is not a backend setting"


def test_production_proxy_files_forward_to_the_backend_and_keep_the_port_private():
    assert "reverse_proxy backend:8000" in read("deploy/Caddyfile")
    prod = read("deploy/docker-compose.prod.yml")
    assert "caddy:2" in prod and "API_DOMAIN:?" in prod       # refuses to start without a domain
    assert "${BACKEND_BIND:-0.0.0.0}:8000:8000" in read("docker-compose.yml")


def test_chroma_is_optional_in_the_docker_image_and_present_in_dev_requirements():
    assert "ARG INSTALL_CHROMA=false" in read("backend/Dockerfile")
    assert "chromadb" not in read("backend/requirements.txt").lower()      # default image stays lean
    assert "chromadb" in read("backend/requirements-chroma.txt").lower()
    assert "-r requirements-chroma.txt" in read("backend/requirements-dev.txt")
    assert "VECTOR_STORE: ${VECTOR_STORE:-faiss}" in read("docker-compose.yml")
