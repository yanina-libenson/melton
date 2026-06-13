"""Money formatting for Argentine pesos (ARS).

Always renders the word 'pesos' and never a bare '$' sign: a '$' is read aloud
by TTS (and often by the model) as "dólares", which is exactly the confusion we
want to avoid on a voice/watch channel. Argentine grouping (thousands with '.',
decimals with ',') keeps large amounts legible on a small screen.
"""

from __future__ import annotations


def format_ars(amount) -> str:
    """Format an ARS amount, e.g. 50000 -> '50.000 pesos', 1500.5 -> '1.500,50 pesos'.

    Falls back to a plain '<value> pesos' if `amount` isn't numeric.
    """
    try:
        value = float(amount)
    except (TypeError, ValueError):
        return f"{amount} pesos"

    if value == int(value):
        whole = f"{int(value):,}".replace(",", ".")
        return f"{whole} pesos"

    # f"{1500.5:,.2f}" -> '1,500.50'; swap separators to Argentine style.
    s = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s} pesos"
