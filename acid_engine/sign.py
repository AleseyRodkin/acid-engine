"""Ed25519 over canonical receipt via local openssl. Not Sigstore."""
from __future__ import annotations

import base64
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from acid_engine.level2.serialization import canonical_serialize, content_hash_of

SIG_SCHEMA = "acid.signature.v1"
ALG = "ed25519"


def _openssl() -> str:
    exe = shutil.which("openssl")
    if not exe:
        raise RuntimeError("openssl not found; Ed25519 sign needs local openssl")
    return exe


def canonical_receipt_bytes(receipt: dict[str, Any]) -> bytes:
    text = canonical_serialize(receipt)
    if "proven_pure" in text:
        raise ValueError("receipt must not contain proven_pure")
    return text.encode("utf-8")


def keygen(out_dir: str | Path) -> tuple[Path, Path]:
    dest = Path(out_dir)
    dest.mkdir(parents=True, exist_ok=True)
    secret = dest / "ed25519.secret.pem"
    public = dest / "ed25519.public.pem"
    openssl = _openssl()
    subprocess.run(
        [openssl, "genpkey", "-algorithm", "ED25519", "-out", str(secret)],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [openssl, "pkey", "-in", str(secret), "-pubout", "-out", str(public)],
        check=True,
        capture_output=True,
        text=True,
    )
    return secret, public


def sign_receipt(receipt: dict[str, Any], secret_pem: str | Path) -> dict[str, Any]:
    payload = canonical_receipt_bytes(receipt)
    openssl = _openssl()
    with tempfile.TemporaryDirectory() as tmp:
        msg = Path(tmp) / "receipt.canon"
        out = Path(tmp) / "receipt.sig"
        msg.write_bytes(payload)
        subprocess.run(
            [
                openssl,
                "pkeyutl",
                "-sign",
                "-inkey",
                str(secret_pem),
                "-rawin",
                "-in",
                str(msg),
                "-out",
                str(out),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        raw = out.read_bytes()
    return {
        "schema": SIG_SCHEMA,
        "alg": ALG,
        "receipt_hash": content_hash_of(receipt),
        "sig": base64.standard_b64encode(raw).decode("ascii"),
    }


def verify_receipt(
    receipt: dict[str, Any],
    signature: dict[str, Any],
    public_pem: str | Path,
) -> None:
    if signature.get("schema") != SIG_SCHEMA:
        raise ValueError("unknown signature schema")
    if signature.get("alg") != ALG:
        raise ValueError("unknown signature alg")
    if signature.get("receipt_hash") != content_hash_of(receipt):
        raise ValueError("receipt_hash does not match receipt")
    raw_sig = base64.standard_b64decode(str(signature["sig"]))
    payload = canonical_receipt_bytes(receipt)
    openssl = _openssl()
    with tempfile.TemporaryDirectory() as tmp:
        sig_path = Path(tmp) / "sig.bin"
        msg = Path(tmp) / "receipt.canon"
        sig_path.write_bytes(raw_sig)
        msg.write_bytes(payload)
        proc = subprocess.run(
            [
                openssl,
                "pkeyutl",
                "-verify",
                "-pubin",
                "-inkey",
                str(public_pem),
                "-rawin",
                "-in",
                str(msg),
                "-sigfile",
                str(sig_path),
            ],
            capture_output=True,
            text=True,
        )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "verify failed").strip()
        raise ValueError(f"signature mismatch: {err}")
