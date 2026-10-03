FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen
COPY api.py .
EXPOSE 8000
CMD ["uv", "run", "--frozen", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
