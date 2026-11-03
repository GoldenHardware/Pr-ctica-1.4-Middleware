"""
Manejo de errores con un formato común para toda la API:

    {"error": "mensaje para el cliente", "error_code": "CODIGO", ...}

- 4xx HTTP_ERROR (404, 405...): errores HTTP normales, p. ej. una ruta que no existe.
- 422 VALIDATION_ERROR: datos de entrada no válidos (incluye la lista de errores por campo).
- 500 INTERNAL_ERROR: cualquier excepción no controlada. El cliente recibe un
  mensaje genérico y el request_id; el detalle completo (stacktrace) solo va al log.
"""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import logger

MENSAJES = {
    "missing": "Campo obligatorio",
    "string_too_short": "Debe tener al menos {min_length} carácter(es)",
    "string_too_long": "No puede superar {max_length} caracteres",
    "string_type": "Debe ser un texto",
    "int_parsing": "Debe ser un número entero",
    "int_type": "Debe ser un número entero",
    "greater_than": "Debe ser mayor que {gt}",
    "extra_forbidden": "Campo no permitido",
    "json_invalid": "El cuerpo no es un JSON válido",
}


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Convierte los errores de Pydantic en un 422 claro y con el formato común."""
    errors = []
    for err in exc.errors():
        # loc = ("body", "title") -> nos quedamos con "title"
        campo = ".".join(str(p) for p in err["loc"] if p != "body") or "body"
        plantilla = MENSAJES.get(err["type"])
        mensaje = plantilla.format(**err.get("ctx", {})) if plantilla else err["msg"]
        errors.append({"campo": campo, "mensaje": mensaje})

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "error": "Error de validación en los datos enviados",
            "error_code": "VALIDATION_ERROR",
            "request_id": _request_id(request),
            "errors": errors,
        },
    )


HTTP_ERROR_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
}


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Errores HTTP (404, 405, HTTPException lanzadas en los routers) con el formato común."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": str(exc.detail),
            "error_code": HTTP_ERROR_CODES.get(exc.status_code, "HTTP_ERROR"),
            "request_id": _request_id(request),
        },
        headers=getattr(exc, "headers", None),
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Handler global para excepciones no controladas.

    - Al LOG: el error completo con stacktrace (logger.exception), para poder depurarlo.
    - Al CLIENTE: un mensaje genérico. Nunca el stacktrace, porque revelaría
      rutas de archivos, librerías y lógica interna que un atacante podría usar.
    """
    logger.exception(
        "Excepción no controlada en %s %s [request_id=%s]",
        request.method, request.url.path, _request_id(request),
        exc_info=exc,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Error interno del servidor",
            "error_code": "INTERNAL_ERROR",
            "request_id": _request_id(request),
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Registra en la app los manejadores de errores del proyecto."""
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    # Red de seguridad: si una excepción escapa incluso del middleware.
    app.add_exception_handler(Exception, unhandled_exception_handler)
