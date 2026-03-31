# github-token

A minimal Docker image that generates short-lived GitHub App installation tokens.
Replace inline bash JWT generation in your Kubernetes jobs and CI pipelines with a
single container invocation.

## Quick start

```bash
docker run --rm \
  -e GITHUB_APP_ID=12345 \
  -e GITHUB_APP_INSTALLATION_ID=67890 \
  -e GITHUB_APP_PRIVATE_KEY="$(cat /path/to/key.pem)" \
  enponsba/github-token:latest
```

The token is printed to stdout.

Alternatively, mount the key as a file:

```bash
docker run --rm \
  -e GITHUB_APP_ID=12345 \
  -e GITHUB_APP_INSTALLATION_ID=67890 \
  -v /path/to/key.pem:/etc/github/GITHUB_APP_PRIVATE_KEY:ro \
  enponsba/github-token:latest
```

## Available images

Images are published for every supported Python version and distro combination,
each built for **linux/amd64** and **linux/arm64**:

| Tag | Base |
|-----|------|
| `latest`, `3.13-slim` | `python:3.13-slim` |
| `3.13-alpine` | `python:3.13-alpine` |
| `3.12-slim`, `3.12` | `python:3.12-slim` |
| `3.12-alpine` | `python:3.12-alpine` |
| `3.11-slim`, `3.11` | `python:3.11-slim` |
| `3.11-alpine` | `python:3.11-alpine` |

Only [actively maintained](https://devguide.python.org/versions/) CPython versions
are supported. End-of-life versions are removed automatically.

## Configuration

All configuration is via environment variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `GITHUB_APP_ID` | Yes | GitHub App ID |
| `GITHUB_APP_INSTALLATION_ID` | Yes | Installation ID for the target org/repo |
| `GITHUB_APP_PRIVATE_KEY` | No | PEM-encoded private key as a string |
| `GITHUB_APP_PRIVATE_KEY_PATH` | No | Path to PEM file (default: `/etc/github/GITHUB_APP_PRIVATE_KEY`) |
| `GITHUB_TOKEN_PERMISSIONS` | No | JSON object of token permissions (e.g., `{"contents":"read"}`) |
| `GITHUB_TOKEN_REPOSITORIES` | No | Comma-separated list of repository names to scope the token to |
| `GITHUB_TOKEN_OUTPUT` | No | Output mode: `stdout` (default), `file:/path/to/file`, or `github-output` |

Either `GITHUB_APP_PRIVATE_KEY` or `GITHUB_APP_PRIVATE_KEY_PATH` must be provided.
If both are set, the literal key string takes precedence.

## Kubernetes example

```yaml
containers:
- name: get-token
  image: enponsba/github-token:latest
  env:
    - name: GITHUB_APP_ID
      valueFrom:
        secretKeyRef:
          name: github-app-secret
          key: GITHUB_APP_ID
    - name: GITHUB_APP_INSTALLATION_ID
      valueFrom:
        secretKeyRef:
          name: github-app-secret
          key: GITHUB_APP_INSTALLATION_ID
    - name: GITHUB_APP_PRIVATE_KEY
      valueFrom:
        secretKeyRef:
          name: github-app-secret
          key: GITHUB_APP_PRIVATE_KEY
```

See [`examples/`](examples/) for complete Job and ArgoCD hook manifests.

## How it works

1. Reads the GitHub App private key from a file or environment variable
2. Constructs an RS256-signed JWT using only the Python standard library
3. Exchanges the JWT for a short-lived installation access token via the GitHub API
4. Outputs the token to stdout (or a file / `$GITHUB_OUTPUT`)

Zero external Python dependencies. The image contains only CPython and the
application source code.

## Development

```bash
# Install dev dependencies
uv sync --group dev

# Run tests
uv run pytest

# Lint and format
uvx ruff check src/ tests/
uvx ruff format --check src/ tests/

# Type check
uvx ty check src/ tests/
```

### Pre-commit hooks

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

## License

[Apache License 2.0](LICENSE)
