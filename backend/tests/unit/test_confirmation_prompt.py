"""Tests for the confirmation summary prompt (Phase 1, step 5-lite)."""

from app.services.execution_service import format_confirmation_prompt


def test_renders_money_summary_before_confirming():
    out = format_confirmation_prompt(
        {
            "accion": "Transferencia de pesos",
            "monto": 1,
            "destinatario": "Yanina Libenson",
            "irreversible": True,
        }
    )
    assert "Monto: 1 pesos" in out
    assert "Destinatario: Yanina Libenson" in out
    assert "irreversible" in out.lower()
    assert "¿Confirmás?" in out


def test_skips_none_values():
    out = format_confirmation_prompt({"monto": 5, "destinatario": None, "concepto": "VAR"})
    assert "Destinatario" not in out
    assert "Monto: 5 pesos" in out


def test_empty_summary_falls_back():
    assert "Confirmás" in format_confirmation_prompt(None)
    assert "Confirmás" in format_confirmation_prompt({})
