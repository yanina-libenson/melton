"""Tests for ARS money formatting (always 'pesos', never a bare '$')."""

from app.utils.money import format_ars


def test_groups_thousands_argentine_style():
    assert format_ars(50000) == "50.000 pesos"
    assert format_ars(1000000) == "1.000.000 pesos"


def test_small_amounts():
    assert format_ars(1) == "1 pesos"
    assert format_ars(0) == "0 pesos"


def test_decimals_use_comma():
    assert format_ars(1500.5) == "1.500,50 pesos"


def test_never_emits_dollar_sign_or_ars():
    out = format_ars(1234.56)
    assert "$" not in out
    assert "ARS" not in out
    assert out.endswith("pesos")


def test_non_numeric_falls_back():
    assert format_ars("muchos") == "muchos pesos"
