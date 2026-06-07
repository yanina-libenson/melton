"""Tests for the confirmation intent classifier (Phase 1, step 3c)."""

import pytest

from app.services.confirmation_intent import classify_confirmation


@pytest.mark.parametrize(
    "text",
    ["sí", "Si", "dale", "confirmo", "ok, hacelo", "listo", "perfecto, mandá"],
)
def test_yes(text):
    assert classify_confirmation(text) == "yes"


@pytest.mark.parametrize(
    "text",
    ["no", "cancelá", "mejor no", "no sé", "pará", "ni en pedo", "stop"],
)
def test_no(text):
    assert classify_confirmation(text) == "no"


def test_negative_wins_over_positive():
    # The review's example: mixed signal on an irreversible action -> cancel.
    assert classify_confirmation("eh, dale... no sé") == "no"
    assert classify_confirmation("dale pero no") == "no"


@pytest.mark.parametrize("text", ["", "qué hora es?", "contame más", "buenos aires"])
def test_ambiguous(text):
    assert classify_confirmation(text) == "ambiguous"
