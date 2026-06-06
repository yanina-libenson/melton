"""Classify a user's reply to a confirmation prompt as yes / no / ambiguous.

Spanish (Argentine) word lists ported from the ai-agent-v2 voice agent. For
irreversible actions (money), negatives take precedence over positives so an
ambiguous reply like "eh, dale... no sé" resolves to NO (cancel), never a
mistaken approval. A reply with no clear signal is "ambiguous" -> re-ask.
"""

import re

_POSITIVE = {
    "sí", "si", "yes", "ok", "okay", "vale", "dale", "bárbaro", "barbaro",
    "perfecto", "genial", "adelante", "confirmo", "confirmar", "confirmá",
    "confirma", "manda", "mandá", "mándalo", "mandalo", "hacelo", "hazlo",
    "listo", "bueno", "correcto", "obvio", "sip", "claro",
}

_NEGATIVE = {
    "no", "cancel", "cancelá", "cancela", "cancelar", "para", "pará",
    "frená", "frena", "detente", "stop", "basta", "negativo", "nop",
}

# Phrases checked against the whole normalized string.
_NEGATIVE_PHRASES = ("mejor no", "no sé", "no se", "ni en pedo", "para nada")


def classify_confirmation(text: str) -> str:
    """Return 'yes', 'no', or 'ambiguous' for a confirmation reply."""
    if not text:
        return "ambiguous"

    normalized = text.lower().strip()

    if any(phrase in normalized for phrase in _NEGATIVE_PHRASES):
        return "no"

    tokens = set(re.findall(r"[a-záéíóúñü]+", normalized))

    # Negative wins: safer to cancel an irreversible action on mixed signals.
    if tokens & _NEGATIVE:
        return "no"
    if tokens & _POSITIVE:
        return "yes"
    return "ambiguous"
