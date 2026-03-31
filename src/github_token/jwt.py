"""RS256 JWT generation using only the Python standard library.

Parses a PKCS#1 or PKCS#8 PEM private key, then signs the JWT with
raw RSA (RSASSA-PKCS1-v1_5 with SHA-256) -- no openssl binary or
third-party libraries required.
"""

from __future__ import annotations

import base64
import hashlib
import json
import time


def create_jwt(app_id: str, private_key_pem: str, duration: int = 600) -> str:
    """Create a signed JWT for GitHub App authentication.

    Args:
        app_id: The GitHub App ID (used as the ``iss`` claim).
        private_key_pem: PEM-encoded RSA private key.
        duration: Token lifetime in seconds (max 600).

    Returns:
        The signed JWT string.
    """
    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    payload = {"iat": now - 60, "exp": now + duration, "iss": app_id}

    segments = [
        _b64url(json.dumps(header, separators=(",", ":")).encode()),
        _b64url(json.dumps(payload, separators=(",", ":")).encode()),
    ]
    signing_input = f"{segments[0]}.{segments[1]}".encode()

    n, d = _parse_rsa_private_key(private_key_pem)
    signature = _rsassa_pkcs1_v15_sign(signing_input, n, d)

    segments.append(_b64url(signature))
    return ".".join(segments)


# ---------------------------------------------------------------------------
# Base64url helpers
# ---------------------------------------------------------------------------


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


# ---------------------------------------------------------------------------
# Minimal ASN.1 / DER parser (just enough for RSA private keys)
# ---------------------------------------------------------------------------


def _parse_rsa_private_key(pem: str) -> tuple[int, int]:
    """Extract (n, d) from a PEM RSA private key (PKCS#1 or PKCS#8)."""
    lines = [line for line in pem.strip().splitlines() if not line.startswith("-----")]
    der = base64.b64decode("".join(lines))

    if b"PRIVATE KEY" in pem.encode() and b"RSA PRIVATE KEY" not in pem.encode():
        der = _unwrap_pkcs8(der)

    return _parse_pkcs1_der(der)


def _unwrap_pkcs8(der: bytes) -> bytes:
    """Strip the PKCS#8 wrapper to get the inner PKCS#1 key bytes."""
    data, _ = _read_asn1_element(der, 0)
    offset = 0
    _version, offset = _read_asn1_element(data, offset)
    _algo_seq, offset = _read_asn1_element(data, offset)
    octet_string, _ = _read_asn1_element(data, offset)
    return bytes(octet_string)


def _parse_pkcs1_der(der: bytes) -> tuple[int, int]:
    """Parse a PKCS#1 RSAPrivateKey and return (n, d)."""
    seq, _ = _read_asn1_element(der, 0)
    offset = 0
    _version, offset = _read_asn1_integer(seq, offset)
    n, offset = _read_asn1_integer(seq, offset)
    _e, offset = _read_asn1_integer(seq, offset)
    d, offset = _read_asn1_integer(seq, offset)
    return (n, d)


def _read_asn1_element(data: bytes | memoryview, offset: int) -> tuple[memoryview, int]:
    """Read one ASN.1 TLV element and return (value_bytes, new_offset)."""
    view = memoryview(data)
    tag_end = offset + 1  # noqa: F841
    length_byte = view[offset + 1]
    if length_byte & 0x80 == 0:
        length = length_byte
        value_start = offset + 2
    else:
        num_len_bytes = length_byte & 0x7F
        length = int.from_bytes(view[offset + 2 : offset + 2 + num_len_bytes], "big")
        value_start = offset + 2 + num_len_bytes
    value_end = value_start + length
    return view[value_start:value_end], value_end


def _read_asn1_integer(data: bytes | memoryview, offset: int) -> tuple[int, int]:
    """Read an ASN.1 INTEGER and return (python int, new_offset)."""
    element, new_offset = _read_asn1_element(data, offset)
    return int.from_bytes(element, "big", signed=False), new_offset


# ---------------------------------------------------------------------------
# RSASSA-PKCS1-v1_5 signature (RFC 8017 section 8.2)
# ---------------------------------------------------------------------------

_SHA256_DIGEST_INFO_PREFIX = bytes.fromhex("3031300d060960864801650304020105000420")


def _rsassa_pkcs1_v15_sign(message: bytes, n: int, d: int) -> bytes:
    """Produce an RSASSA-PKCS1-v1_5 signature over *message*."""
    digest = hashlib.sha256(message).digest()
    digest_info = _SHA256_DIGEST_INFO_PREFIX + digest

    k = (n.bit_length() + 7) // 8  # key length in bytes
    pad_len = k - 3 - len(digest_info)
    if pad_len < 8:
        raise ValueError("RSA key too short for SHA-256 signature")
    em = b"\x00\x01" + (b"\xff" * pad_len) + b"\x00" + digest_info

    m_int = int.from_bytes(em, "big")
    s_int = pow(m_int, d, n)
    return s_int.to_bytes(k, "big")
