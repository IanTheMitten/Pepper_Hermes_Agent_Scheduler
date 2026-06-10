from __future__ import annotations

from collections.abc import Callable

EmbedFn = Callable[[str], list[float]]

_cached_fn: EmbedFn | None = None
_cached_model = None


def _get_model():
    global _cached_model
    if _cached_model is None:
        from fastembed import TextEmbedding

        _cached_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    return _cached_model


def get_embed_fn() -> EmbedFn:
    """Return a cached embedding function backed by fastembed.

    Cheap to call: the heavy fastembed model is constructed lazily on the first
    actual embedding call, not when this factory runs -- so callers that end up
    not embedding (e.g. a capture with no learned types) never load the model.
    Tests never call this; they inject a deterministic fake EmbedFn instead.
    """
    global _cached_fn
    if _cached_fn is None:

        def _embed(text: str) -> list[float]:
            model = _get_model()
            return list(next(iter(model.embed([text]))))

        _cached_fn = _embed
    return _cached_fn
