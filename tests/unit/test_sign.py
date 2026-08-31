"""Ed25519 on canonical receipt. Tamper fails. Not Sigstore."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from acid_engine.level2.serialization import content_hash_of
from acid_engine.sign import keygen, sign_receipt, verify_receipt

ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.skipif(shutil.which("openssl") is None, reason="openssl missing")


def _receipt() -> dict:
    return {
        "schema": "acid.receipt.v1",
        "script_name": "n_plus_one",
        "verdict": {"status": "PASS", "level": "structural", "message": "ok", "property": None},
        "output": {"n": 4},
    }


def test_sign_verify_roundtrip():
    rec = _receipt()
    with tempfile.TemporaryDirectory() as tmp:
        secret, public = keygen(tmp)
        sig = sign_receipt(rec, secret)
        assert sig["alg"] == "ed25519"
        assert "proven_pure" not in json.dumps(sig)
        verify_receipt(rec, sig, public)


def test_tampered_receipt_fails():
    rec = _receipt()
    with tempfile.TemporaryDirectory() as tmp:
        secret, public = keygen(tmp)
        sig = sign_receipt(rec, secret)
        rec["output"] = {"n": 99}
        try:
            verify_receipt(rec, sig, public)
            assert False
        except ValueError:
            pass


def test_forged_hash_still_fails_crypto():
    rec = _receipt()
    with tempfile.TemporaryDirectory() as tmp:
        secret, public = keygen(tmp)
        sig = sign_receipt(rec, secret)
        rec["output"] = {"n": 99}
        sig["receipt_hash"] = content_hash_of(rec)
        try:
            verify_receipt(rec, sig, public)
            assert False
        except ValueError:
            pass


def test_cli_receipt_verify():
    rec = _receipt()
    with tempfile.TemporaryDirectory() as tmp:
        secret, public = keygen(tmp)
        rec_path = Path(tmp) / "r.json"
        rec_path.write_text(json.dumps(rec), encoding="utf-8")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT)
        sign = subprocess.run(
            [
                sys.executable, "-m", "acid_engine", "receipt",
                "--sign", str(rec_path), "--key", str(secret),
                "--out", str(Path(tmp) / "r.sig.json"),
            ],
            capture_output=True, text=True, env=env, cwd=str(ROOT),
        )
        assert sign.returncode == 0, sign.stderr + sign.stdout
        ok = subprocess.run(
            [
                sys.executable, "-m", "acid_engine", "receipt",
                "--verify", str(rec_path),
                "--sig", str(Path(tmp) / "r.sig.json"),
                "--pubkey", str(public),
            ],
            capture_output=True, text=True, env=env, cwd=str(ROOT),
        )
        assert ok.returncode == 0, ok.stderr + ok.stdout
        assert "[OK]" in ok.stdout
        tampered = json.loads(rec_path.read_text(encoding="utf-8"))
        tampered["output"] = {"n": 0}
        rec_path.write_text(json.dumps(tampered), encoding="utf-8")
        bad = subprocess.run(
            [
                sys.executable, "-m", "acid_engine", "receipt",
                "--verify", str(rec_path),
                "--sig", str(Path(tmp) / "r.sig.json"),
                "--pubkey", str(public),
            ],
            capture_output=True, text=True, env=env, cwd=str(ROOT),
        )
        assert bad.returncode != 0
        assert "PASS" not in bad.stdout or "ERROR" in bad.stdout
