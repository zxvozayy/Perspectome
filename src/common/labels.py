"""Held-out answer values as option labels: 7.0 -> "7", "quite_a_lot" stays, blanks -> None."""

import math


def answer_label(value):
    if value is None or value == "":
        return None
    if isinstance(value, float):
        if math.isnan(value):
            return None
        if value.is_integer():
            return str(int(value))
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if hasattr(value, "item"):  # numpy scalars
        return answer_label(value.item())
    text = str(value).strip()
    try:
        number = float(text)
    except ValueError:
        return text or None
    return str(int(number)) if number.is_integer() else text
