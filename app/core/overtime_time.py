"""Cálculo de horas extra a partir de franjas horarias."""

from __future__ import annotations

from datetime import time
from decimal import Decimal, ROUND_HALF_UP

from app.core.exceptions import bad_request


def calc_overtime_hours(start: time, end: time) -> Decimal:
    """Horas decimales entre dos horas del mismo día (fin estrictamente posterior al inicio)."""
    start_m = start.hour * 60 + start.minute
    end_m = end.hour * 60 + end.minute
    if end_m <= start_m:
        raise bad_request("La hora de fin debe ser posterior a la hora de inicio")
    minutes = end_m - start_m
    hours = (Decimal(minutes) / Decimal(60)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if hours <= 0:
        raise bad_request("El rango horario debe ser mayor a cero")
    return hours


def format_time_24h(value: time) -> str:
    return value.strftime("%H:%M")


def format_time_range_label(start: time | None, end: time | None) -> str | None:
    if start is None or end is None:
        return None
    return f"{format_time_24h(start)} – {format_time_24h(end)}"
