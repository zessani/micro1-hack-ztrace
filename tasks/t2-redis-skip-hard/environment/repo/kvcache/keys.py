"""Namespaced cache key builder."""
import warnings


def make_key(*parts, sep=":"):
    if sep != ":":
        warnings.warn("custom key separators are deprecated", DeprecationWarning, stacklevel=2)
    cleaned = [str(p).strip().replace(" ", "_") for p in parts if p not in (None, "")]
    if not cleaned:
        raise ValueError("at least one key part is required")
    return sep.join(cleaned)


def split_key(key, sep=":"):
    return key.split(sep)
