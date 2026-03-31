"""Tests for the pure-Python RS256 JWT implementation."""

from __future__ import annotations

import base64
import json
import subprocess
import tempfile
import time
from pathlib import Path

from github_token.jwt import (
    _b64url,
    _parse_rsa_private_key,
    _rsassa_pkcs1_v15_sign,
    create_jwt,
)


class TestB64Url:
    def test_no_padding(self) -> None:
        result = _b64url(b"\x00\x01\x02")
        assert "=" not in result

    def test_url_safe_chars(self) -> None:
        result = _b64url(b"\xff\xfe\xfd")
        assert "+" not in result
        assert "/" not in result

    def test_round_trip(self) -> None:
        data = b"hello world"
        encoded = _b64url(data)
        padding = "=" * (-len(encoded) % 4)
        decoded = base64.urlsafe_b64decode(encoded + padding)
        assert decoded == data


class TestParseRSAPrivateKey:
    def test_pkcs1_format(self, private_key_pem: str) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pkcs1_path = Path(tmp) / "pkcs1.pem"
            subprocess.run(
                [
                    "openssl",
                    "rsa",
                    "-in",
                    "/dev/stdin",
                    "-out",
                    str(pkcs1_path),
                    "-traditional",
                ],
                input=private_key_pem.encode(),
                check=True,
                capture_output=True,
            )
            pkcs1_pem = pkcs1_path.read_text()

        n, d = _parse_rsa_private_key(pkcs1_pem)
        assert n > 0
        assert d > 0
        assert n.bit_length() >= 2048

    def test_pkcs8_format(self, private_key_pem: str) -> None:
        n, d = _parse_rsa_private_key(private_key_pem)
        assert n > 0
        assert d > 0


class TestRSASignature:
    def test_signature_verifies_with_openssl(
        self, private_key_pem: str, public_key_pem: str
    ) -> None:
        message = b"test message to sign"
        n, d = _parse_rsa_private_key(private_key_pem)
        sig = _rsassa_pkcs1_v15_sign(message, n, d)

        with tempfile.TemporaryDirectory() as tmp:
            sig_path = Path(tmp) / "sig.bin"
            pub_path = Path(tmp) / "pub.pem"
            msg_path = Path(tmp) / "msg.txt"

            sig_path.write_bytes(sig)
            pub_path.write_text(public_key_pem)
            msg_path.write_bytes(message)

            result = subprocess.run(
                [
                    "openssl",
                    "dgst",
                    "-sha256",
                    "-verify",
                    str(pub_path),
                    "-signature",
                    str(sig_path),
                    str(msg_path),
                ],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, f"openssl verify failed: {result.stderr}"

    def test_digest_matches(self, private_key_pem: str) -> None:
        message = b"another test"
        n, d = _parse_rsa_private_key(private_key_pem)
        sig = _rsassa_pkcs1_v15_sign(message, n, d)
        assert len(sig) == (n.bit_length() + 7) // 8


class TestCreateJWT:
    def test_structure(self, private_key_pem: str) -> None:
        token = create_jwt("12345", private_key_pem, duration=600)
        parts = token.split(".")
        assert len(parts) == 3

        header = json.loads(self._b64decode(parts[0]))
        assert header == {"alg": "RS256", "typ": "JWT"}

        payload = json.loads(self._b64decode(parts[1]))
        assert payload["iss"] == "12345"
        assert "iat" in payload
        assert "exp" in payload
        assert payload["exp"] - payload["iat"] <= 660

    def test_timing_claims(self, private_key_pem: str) -> None:
        before = int(time.time())
        token = create_jwt("99", private_key_pem)
        after = int(time.time())

        payload = json.loads(self._b64decode(token.split(".")[1]))
        assert payload["iat"] >= before - 61
        assert payload["iat"] <= after - 59
        assert payload["exp"] >= before + 539
        assert payload["exp"] <= after + 601

    def test_signature_is_valid(self, private_key_pem: str, public_key_pem: str) -> None:
        token = create_jwt("42", private_key_pem)
        parts = token.split(".")
        signing_input = f"{parts[0]}.{parts[1]}".encode()

        padding = "=" * (-len(parts[2]) % 4)
        signature = base64.urlsafe_b64decode(parts[2] + padding)

        with tempfile.TemporaryDirectory() as tmp:
            sig_path = Path(tmp) / "sig.bin"
            pub_path = Path(tmp) / "pub.pem"
            msg_path = Path(tmp) / "msg.txt"

            sig_path.write_bytes(signature)
            pub_path.write_text(public_key_pem)
            msg_path.write_bytes(signing_input)

            result = subprocess.run(
                [
                    "openssl",
                    "dgst",
                    "-sha256",
                    "-verify",
                    str(pub_path),
                    "-signature",
                    str(sig_path),
                    str(msg_path),
                ],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0

    @staticmethod
    def _b64decode(s: str) -> bytes:
        padding = "=" * (-len(s) % 4)
        return base64.urlsafe_b64decode(s + padding)
