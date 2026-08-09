# ============================================================
#   J–COMPRESSION MODULE (TIMDR / Λ–τ–ρ / Twist Operator)
# ============================================================
#
# UWAGA: plik przemianowany z modulKompresjiJ.py -> j_compression.py,
# żeby zgadzał się z importem w core/__init__.py
# (from .j_compression import j_compress, j_decompress, j_hash),
# który wcześniej powodował ModuleNotFoundError przy `import core`.
# Treść modułu bez zmian.

import hashlib
import struct

MAGIC = b'JCOMP'  # znacznik skrętu – pozwala wykryć kompresję

def j_core_reduce(data: bytes) -> bytes:
    """Minimalna redukcja topologiczna: Λ–τ–ρ."""
    out = bytearray()
    last = 0
    for b in data:
        d = b ^ last
        out.append(d)
        last = b
    return bytes(out)

def j_core_restore(data: bytes) -> bytes:
    """Odwrócenie redukcji."""
    out = bytearray()
    last = 0
    for d in data:
        b = d ^ last
        out.append(b)
        last = b
    return bytes(out)

def j_compress(raw: bytes) -> bytes:
    core = j_core_reduce(raw)
    return MAGIC + core

def j_decompress(blob: bytes) -> bytes:
    if not blob.startswith(MAGIC):
        raise ValueError("Plik nie jest w formacie J–compression.")
    core = blob[len(MAGIC):]
    return j_core_restore(core)

def j_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
