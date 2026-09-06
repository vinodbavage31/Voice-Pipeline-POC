import logging
from contextlib import contextmanager
from typing import Any, Iterator

from app.config import settings

logger = logging.getLogger(__name__)

try:
    from langfuse import Langfuse
except ImportError:
    Langfuse = None

_client = None


def _get_client():
    global _client
    if _client is None and Langfuse and settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY:
        _client = Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
        )
    return _client


@contextmanager
def trace_stage(name: str, metadata: dict[str, Any] | None = None) -> Iterator[None]:
    """Trace a pipeline stage when Langfuse is configured; otherwise remain a no-op."""
    client = _get_client()
    if client is None:
        yield
        return

    try:
        span_context = client.start_as_current_span(name=name)
    except Exception:
        logger.exception("Langfuse tracing failed to start for stage %s", name)
        yield
        return

    try:
        with span_context as span:
            if metadata:
                span.update(input=metadata)
            yield
    finally:
        try:
            client.flush()
        except Exception:
            logger.exception("Langfuse flush failed")
