from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_dockerfile_uses_python_311_and_gunicorn_uvicorn_worker():
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "FROM python:3.11" in dockerfile
    assert "gunicorn" in dockerfile
    assert "uvicorn.workers.UvicornWorker" in dockerfile
    assert "EXPOSE 8000" in dockerfile


def test_docker_compose_includes_backend_and_postgres():
    compose = (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "backend:" in compose
    assert "postgres:" in compose
    assert "DATABASE_URL:" in compose
    assert "postgresql+psycopg2://" in compose
    assert "sqlite" not in compose.lower()
