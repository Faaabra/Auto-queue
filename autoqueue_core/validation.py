"""Validation shared by forms, imports and persisted configuration."""
import ipaddress
import re


def normalize_address(value):
    if not isinstance(value, str):
        raise ValueError("La dirección debe ser texto.")
    value = re.sub(r"^(?:client\.)?connect\s+", "", value.strip(), flags=re.I)
    value = value.strip('"').strip()
    if not value or len(value) > 260:
        raise ValueError("Introduce una IP o dominio válido.")
    host, separator, port = value.partition(":")
    if separator and (not re.fullmatch(r"[0-9]{1,5}", port) or not 1 <= int(port) <= 65535):
        raise ValueError("El puerto debe estar entre 1 y 65535.")
    if re.fullmatch(r"[0-9.]+", host):
        try:
            ipaddress.IPv4Address(host)
        except ValueError as error:
            raise ValueError("La dirección IPv4 no es válida.") from error
    else:
        labels = host.rstrip(".").split(".")
        if len(host) > 253 or any(not re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?", label) for label in labels):
            raise ValueError("El dominio no es válido. Ejemplo: eu.rustoria.co:28015")
    return host.lower() + (f":{int(port)}" if separator else "")


def validate_servers(data):
    if not isinstance(data, dict) or len(data) > 1000:
        raise ValueError("Se espera un objeto JSON con un máximo de 1000 servidores.")
    result = {}
    for alias, record in data.items():
        if not isinstance(alias, str) or not alias.strip() or len(alias) > 100 or any(ord(c) < 32 for c in alias):
            raise ValueError("Cada alias debe contener entre 1 y 100 caracteres, sin controles.")
        if isinstance(record, str):
            record = {"ip": record, "fav": False}
        if not isinstance(record, dict) or not isinstance(record.get("fav", False), bool):
            raise ValueError(f"Formato incorrecto para el servidor '{alias}'.")
        normalized_alias = alias.strip()
        if normalized_alias in result:
            raise ValueError(f"Alias duplicado: {normalized_alias}")
        result[normalized_alias] = {**record, "ip": normalize_address(record.get("ip")), "fav": record.get("fav", False)}
    return result


def validate_settings(data):
    if not isinstance(data, dict):
        raise ValueError("Las preferencias deben ser un objeto JSON.")
    result = {"wake_method": None, "delay": 10, "one_time_mode": False,
              "reconnect_enabled": False, "reconnect_interval": 30, "reduce_motion": False, **data}
    for key, low, high, default in (("delay", 5, 300, 10), ("reconnect_interval", 5, 60, 30)):
        value = result[key]
        result[key] = max(low, min(high, value)) if type(value) is int else default
    for key in ("one_time_mode", "reconnect_enabled", "reduce_motion", "smart_wipe", "password_warning_shown"):
        if key in result and not isinstance(result[key], bool):
            result[key] = False
    if result["wake_method"] not in (None, "smart_plug", "bios", "software"):
        result["wake_method"] = None
    for key in ("active_steam_user", "saved_sys_user"):
        if key in result and not isinstance(result[key], str):
            result.pop(key)
    return result


def version_tuple(value):
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", value.strip())
    return tuple(map(int, match.groups())) if match else None


def is_newer_version(candidate, current):
    latest, installed = version_tuple(candidate), version_tuple(current)
    return latest is not None and installed is not None and latest > installed
