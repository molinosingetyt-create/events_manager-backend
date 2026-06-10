"""Etiquetas de quincena de causación (nómina)."""

from __future__ import annotations

_MONTHS_ES = (
    "",
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
)


def format_causation_quincena(
    year: int | None,
    month: int | None,
    half: int | None,
) -> str | None:
    if year is None or month is None or half is None:
        return None
    if month < 1 or month > 12 or half not in (1, 2):
        return None
    half_label = "1ª" if half == 1 else "2ª"
    return f"{half_label} quincena — {_MONTHS_ES[month]} {year}"
