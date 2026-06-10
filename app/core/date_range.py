"""Utilidades de rangos de fechas (días inclusivos)."""

from __future__ import annotations

from datetime import date

from app.core.exceptions import bad_request


def calc_inclusive_days(start: date, end: date) -> int:
    if end < start:
        raise bad_request("La fecha de fin no puede ser anterior a la de inicio")
    return (end - start).days + 1
