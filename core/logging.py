"""Configuración del logger de la aplicación."""

import logging

logger = logging.getLogger("taskflow")


def setup_logging() -> None:
    """Formato sencillo: hora, nivel y mensaje. Los logs salen por la consola de uvicorn."""
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
