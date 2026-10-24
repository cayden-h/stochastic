"""Quote validator. A fact or clause is usable only if its quote is in the document text."""
import re


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def quote_in_document(quote: str, document_text: str) -> bool:
    return bool(quote.strip()) and _norm(quote) in _norm(document_text)
