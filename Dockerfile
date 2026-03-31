ARG BASE_IMAGE=python:3.13-slim
FROM ${BASE_IMAGE}

LABEL org.opencontainers.image.title="github-token" \
      org.opencontainers.image.description="Generate GitHub App installation tokens" \
      org.opencontainers.image.source="https://github.com/quiquetech/github-token" \
      org.opencontainers.image.licenses="Apache-2.0"

WORKDIR /app

COPY src/ ./src/

RUN python -m compileall -q src/

USER nobody

ENTRYPOINT ["python", "-m", "github_token"]
