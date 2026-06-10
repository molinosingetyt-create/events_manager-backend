"""Descomposición de nombre completo en partes para expediente HR."""

from __future__ import annotations


def split_full_name(full: str) -> tuple[str | None, str | None, str | None, str | None]:
    """
    Heurística para nombres colombianos: dos apellidos al final, el resto son nombres.
    Ej.: «LUIS ALBERTO RAMIREZ JIMENEZ» → LUIS, ALBERTO, RAMIREZ, JIMENEZ.
    """
    parts = [p.strip() for p in full.split() if p.strip()]
    if not parts:
        return None, None, None, None
    if len(parts) == 1:
        return parts[0].upper(), None, None, None
    if len(parts) == 2:
        return parts[0].upper(), None, parts[1].upper(), None
    if len(parts) == 3:
        return parts[0].upper(), None, parts[1].upper(), parts[2].upper()
    first_name = parts[0].upper()
    first_surname = parts[-2].upper()
    second_surname = parts[-1].upper()
    middle = " ".join(parts[1:-2]).strip()
    second_name = middle.upper() if middle else None
    return first_name, second_name, first_surname, second_surname
