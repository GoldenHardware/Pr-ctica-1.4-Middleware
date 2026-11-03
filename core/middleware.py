"""
Middlewares de la aplicación.

Un middleware es código que se ejecuta en TODAS las peticiones, antes y
después del endpoint, sin tener que repetirlo en cada ruta (comportamiento
transversal).

Orden en que pasa una petición (de fuera hacia dentro):

    request_context  ->  CORS  ->  catch_exceptions  ->  router / endpoint
    (tiempo, id, log)              (convierte errores en 500)

y la respuesta vuelve en orden inverso. Por qué este orden:

- request_context va el PRIMERO (más externo) para medir el tiempo total y
  registrar en el log TODAS las respuestas, incluidas las de CORS (preflight
  OPTIONS) y los errores 500. Si fuera por dentro del manejo de errores, una
  excepción saltaría por encima de él y esa petición no tendría ni
  X-Process-Time ni línea de log.
- CORS va en medio para que las respuestas de error también lleven las
  cabeceras CORS. Si no, el navegador mostraría un "error de CORS" en lugar
  del error real.
- catch_exceptions va el ÚLTIMO (más interno, pegado al endpoint): convierte
  la excepción en una respuesta 500 antes de que llegue a los demás, así
  todos los de fuera reciben una respuesta normal a la que añadir cabeceras.
"""

import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import CORS_EXPOSE_HEADERS, CORS_HEADERS, CORS_METHODS, CORS_ORIGINS
from app.core.errors import unhandled_exception_handler
from app.core.logging import logger


async def request_context_middleware(request: Request, call_next):
    """
    Problema que resuelve: saber cuánto tarda cada petición y poder seguirla
    en los logs.

    1. Asigna un X-Request-ID (usa el que mande el cliente o genera uno nuevo).
       Si un usuario reporta un error, con ese id se encuentra en el log.
    2. Mide el tiempo de respuesta y lo añade en la cabecera X-Process-Time (ms).
    3. Escribe una línea de log por petición: método, ruta, estado y tiempo.
    """
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    request.state.request_id = request_id

    start = time.perf_counter()
    response = await call_next(request)
    process_time_ms = (time.perf_counter() - start) * 1000

    response.headers["X-Process-Time"] = f"{process_time_ms:.2f}"
    response.headers["X-Request-ID"] = request_id

    logger.info(
        "%s %s -> %s (%.2f ms) [request_id=%s]",
        request.method, request.url.path, response.status_code, process_time_ms, request_id,
    )
    return response


async def catch_exceptions_middleware(request: Request, call_next):
    """
    Problema que resuelve: que un error inesperado en un endpoint nunca tumbe
    la API ni muestre el stacktrace al cliente. Delega en el handler global
    (core/errors.py), que registra el error completo y devuelve un 500 genérico.
    """
    try:
        return await call_next(request)
    except Exception as exc:  # noqa: BLE001 - queremos capturar cualquier error
        return await unhandled_exception_handler(request, exc)


def register_middlewares(app: FastAPI) -> None:
    """
    Registra los middlewares. Starlette los envuelve en orden inverso: el
    ÚLTIMO que se añade es el más EXTERNO (el primero que ve la petición).
    """
    # 3) Más interno: captura de excepciones.
    app.middleware("http")(catch_exceptions_middleware)

    # 2) CORS: solo el frontend permitido puede llamar a la API desde el navegador.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=CORS_METHODS,
        allow_headers=CORS_HEADERS,
        expose_headers=CORS_EXPOSE_HEADERS,
    )

    # 1) Más externo: tiempo de respuesta, request-id y log.
    app.middleware("http")(request_context_middleware)
