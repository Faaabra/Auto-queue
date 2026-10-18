"""Atomic JSON writes, bounded reads and recovery without overwriting a good backup."""
import json
import logging
import os
from pathlib import Path
import tempfile
import threading

_lock = threading.RLock()
MAX_JSON_BYTES = 2 * 1024 * 1024


def read_json(path):
    with open(path, "rb") as stream:
        payload = stream.read(MAX_JSON_BYTES + 1)
    if len(payload) > MAX_JSON_BYTES:
        raise ValueError("El archivo supera el límite de 2 MB.")
    return json.loads(payload.decode("utf-8-sig"))


def load_json(path, validator, default_factory, on_recovery=None):
    for candidate in (Path(path), Path(str(path) + ".bak")):
        try:
            data = validator(read_json(candidate))
            if candidate != Path(path):
                logging.getLogger("RustAutoQueue").warning("Recuperado desde copia: %s", candidate)
                if on_recovery:
                    on_recovery(str(candidate))
            return data
        except FileNotFoundError:
            continue
        except (ValueError, OSError, UnicodeError) as error:
            logging.getLogger("RustAutoQueue").warning("No se pudo leer %s: %s", candidate, error)
            if on_recovery:
                on_recovery(str(candidate))
    return default_factory()


def _replace_bytes(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def save_json(path, data, validator):
    normalized = validator(data)
    payload = (json.dumps(normalized, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if len(payload) > MAX_JSON_BYTES:
        raise ValueError("La configuración supera el límite de 2 MB.")
    with _lock:
        try:
            previous = validator(read_json(path))
        except (OSError, ValueError, UnicodeError):
            previous = None
        if previous is not None:
            _replace_bytes(str(path) + ".bak", (json.dumps(previous, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        _replace_bytes(path, payload)
