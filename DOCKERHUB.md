# Quick reference

- **Maintained by**: [enponsba](https://github.com/quiquetech/github-token)
- **Where to get help**: [GitHub Issues](https://github.com/quiquetech/github-token/issues)
- **Where to file issues**: [GitHub Issues](https://github.com/quiquetech/github-token/issues)
- **Source**: [github-token](https://github.com/quiquetech/github-token)

# Supported tags

Tags follow the pattern `<python>-<distro>` for every
[actively maintained](https://devguide.python.org/versions/) CPython version.
End-of-life versions are removed automatically.

| Pattern | Example | Description |
|---------|---------|-------------|
| `latest` | | Newest Python + slim (recommended) |
| `<python>-slim` | `3.13-slim` | Debian slim variant |
| `<python>-alpine` | `3.13-alpine` | Alpine variant |
| `<python>` | `3.13` | Alias for `<python>-slim` |
| `<python>-<distro>-<version>` | `3.13-slim-v1.2.0` | Immutable release tag |

All tags are published for **linux/amd64** and **linux/arm64**.

See the [Tags tab](https://hub.docker.com/r/enponsba/github-token/tags) for
the full list of currently available images.

# What is `github-token`?

A minimal Docker image that generates short-lived
[GitHub App installation tokens](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app).
Replace inline bash JWT generation in your Kubernetes jobs and CI pipelines
with a single container invocation.

**Zero external Python dependencies.** The image contains only CPython and the
application source code.

## How it works

1. Reads the GitHub App private key from a file or environment variable.
2. Constructs an RS256-signed JWT using only the Python standard library.
3. Exchanges the JWT for a short-lived installation access token via the
   GitHub API.
4. Outputs the token to stdout, a file, or `$GITHUB_OUTPUT`.

# How to use this image

The private key can be provided in two ways:

1. **As an environment variable** (`GITHUB_APP_PRIVATE_KEY`) -- pass the PEM
   string directly. No volume mount required.
2. **As a file path** (`GITHUB_APP_PRIVATE_KEY_PATH`) -- mount the PEM file
   into the container. Defaults to `/etc/github/GITHUB_APP_PRIVATE_KEY`.

If both are set, the environment variable takes precedence.

## Pass the key as an environment variable

```bash
docker run --rm \
  -e GITHUB_APP_ID=12345 \
  -e GITHUB_APP_INSTALLATION_ID=67890 \
  -e GITHUB_APP_PRIVATE_KEY="$(cat /path/to/key.pem)" \
  enponsba/github-token:latest
```

The token is printed to stdout.

## Pass the key as a mounted file

```bash
docker run --rm \
  -e GITHUB_APP_ID=12345 \
  -e GITHUB_APP_INSTALLATION_ID=67890 \
  -v /path/to/key.pem:/etc/github/GITHUB_APP_PRIVATE_KEY:ro \
  enponsba/github-token:latest
```

## Scoped permissions

Request only the permissions you need:

```bash
docker run --rm \
  -e GITHUB_APP_ID=12345 \
  -e GITHUB_APP_INSTALLATION_ID=67890 \
  -e GITHUB_APP_PRIVATE_KEY="$(cat /path/to/key.pem)" \
  -e GITHUB_TOKEN_PERMISSIONS='{"contents":"read","pull_requests":"write"}' \
  -e GITHUB_TOKEN_REPOSITORIES='my-repo,other-repo' \
  enponsba/github-token:latest
```

## Writing the token to a file

```bash
docker run --rm \
  -e GITHUB_APP_ID=12345 \
  -e GITHUB_APP_INSTALLATION_ID=67890 \
  -e GITHUB_APP_PRIVATE_KEY="$(cat /path/to/key.pem)" \
  -e GITHUB_TOKEN_OUTPUT=file:/shared/token \
  -v /tmp/shared:/shared \
  enponsba/github-token:latest
```

## Kubernetes init container

Use as an init container to provide a token to your main workload. The private
key can be injected directly from a Secret as an environment variable --
no volume mount for the key is needed:

```yaml
initContainers:
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
      - name: GITHUB_TOKEN_OUTPUT
        value: "file:/shared/token"
    volumeMounts:
      - name: shared
        mountPath: /shared
```

Complete examples: [Kubernetes Job](https://github.com/quiquetech/github-token/blob/main/examples/k8s-job.yaml) |
[ArgoCD PostSync hook](https://github.com/quiquetech/github-token/blob/main/examples/argocd-postsync.yaml)

# Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GITHUB_APP_ID` | **Yes** | GitHub App ID |
| `GITHUB_APP_INSTALLATION_ID` | **Yes** | Installation ID for the target org/repo |
| `GITHUB_APP_PRIVATE_KEY` | No | PEM-encoded private key as a string |
| `GITHUB_APP_PRIVATE_KEY_PATH` | No | Path to PEM file (default: `/etc/github/GITHUB_APP_PRIVATE_KEY`) |
| `GITHUB_TOKEN_PERMISSIONS` | No | JSON object of [token permissions](https://docs.github.com/en/rest/apps/apps#create-an-installation-access-token-for-an-app) (e.g. `{"contents":"read"}`) |
| `GITHUB_TOKEN_REPOSITORIES` | No | Comma-separated list of repository names to scope the token to |
| `GITHUB_TOKEN_OUTPUT` | No | Output mode (see below) |

Either `GITHUB_APP_PRIVATE_KEY` or `GITHUB_APP_PRIVATE_KEY_PATH` must be
provided. If both are set, the literal key string takes precedence.

## Output modes

| Value | Behavior |
|-------|----------|
| `stdout` (default) | Prints the token to stdout |
| `file:/path/to/file` | Writes the token to the specified file |
| `github-output` | Appends `token=<value>` to `$GITHUB_OUTPUT` for use in GitHub Actions |

# Image variants

## `slim` (default)

Based on Debian `python:<version>-slim`. Recommended for most use cases.

## `alpine`

Based on `python:<version>-alpine`. Smaller image at the cost of musl libc
instead of glibc. Use when image size is the primary concern.

# Architecture support

All images are multi-platform manifests supporting:

- `linux/amd64`
- `linux/arm64`

# Security

- The container runs as the `nobody` user (non-root).
- No external Python dependencies -- only the standard library is used.
- Tokens are short-lived (1 hour) and scoped to the requested permissions.
- The private key is never written to stdout or logs.

For security concerns, see the [security policy](https://github.com/quiquetech/github-token/blob/main/.github/SECURITY.md).

# License

[Apache License 2.0](https://github.com/quiquetech/github-token/blob/main/LICENSE)
