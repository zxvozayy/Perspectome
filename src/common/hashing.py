"""The one persona_set_hash: "sha256:<hex>" of a file's exact bytes."""

import hashlib
from pathlib import Path


def sha256_bytes(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def file_hash(path) -> str:
    return sha256_bytes(Path(path).read_bytes())
