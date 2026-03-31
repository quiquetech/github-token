"""Shared test fixtures."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def rsa_keypair() -> tuple[str, str]:
    """Generate a 2048-bit RSA keypair for testing.

    Returns (private_pem, public_pem).
    Uses ``openssl`` CLI which is available in CI and most dev environments.
    """
    with tempfile.TemporaryDirectory() as tmp:
        key_path = Path(tmp) / "test_key.pem"
        pub_path = Path(tmp) / "test_key_pub.pem"

        subprocess.run(
            ["openssl", "genrsa", "-out", str(key_path), "2048"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["openssl", "rsa", "-in", str(key_path), "-pubout", "-out", str(pub_path)],
            check=True,
            capture_output=True,
        )

        private_pem = key_path.read_text()
        public_pem = pub_path.read_text()

    return private_pem, public_pem


@pytest.fixture(scope="session")
def private_key_pem(rsa_keypair: tuple[str, str]) -> str:
    return rsa_keypair[0]


@pytest.fixture(scope="session")
def public_key_pem(rsa_keypair: tuple[str, str]) -> str:
    return rsa_keypair[1]


@pytest.fixture()
def key_file(private_key_pem: str, tmp_path: Path) -> Path:
    """Write the test private key to a temporary file."""
    p = tmp_path / "test_key.pem"
    p.write_text(private_key_pem)
    return p
