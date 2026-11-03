"""Configuración general de la API (un único sitio para cambiar nombre, versión, prefijo o CORS)."""

import os

APP_NAME = "TaskFlow API"
APP_VERSION = "0.4.0"
APP_DESCRIPTION = "API para gestionar proyectos y tareas (2ºDAW - Frameworks)."

# Entorno de ejecución: "development" (por defecto) o "production".
# Se cambia con la variable de entorno ENVIRONMENT.
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Prefijo común de los recursos de negocio. Si un día cambia el contrato,
# se crea /api/v2 sin romper a los clientes que usan /api/v1.
API_V1_PREFIX = "/api/v1"

# --- CORS -------------------------------------------------------------------
# Orígenes (frontends) que pueden llamar a la API desde el navegador.
# En desarrollo es el servidor de Vite (http://localhost:5173). En producción
# se pasa la URL real con la variable CORS_ORIGINS, separando varias por comas:
#   set CORS_ORIGINS=https://taskflow.midominio.com
_DEFAULT_ORIGINS = {
    "development": "http://localhost:5173,http://127.0.0.1:5173",
    "production": "",  # en producción hay que indicarlo explícitamente
}
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", _DEFAULT_ORIGINS.get(ENVIRONMENT, "")).split(",")
    if o.strip()
]

# Métodos y cabeceras que el frontend puede usar (solo los que la API necesita).
CORS_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
CORS_HEADERS = ["Content-Type", "Authorization", "X-Request-ID"]

# Cabeceras propias que el JavaScript del frontend puede LEER en la respuesta.
# Sin expose_headers el navegador las oculta aunque el servidor las envíe.
CORS_EXPOSE_HEADERS = ["X-Process-Time", "X-Request-ID"]

# Descripción de cada grupo (tag) que aparece en Swagger.
TAGS_METADATA = [
    {"name": "system", "description": "Comprobaciones del servidor: estado, versión y ping."},
    {"name": "projects", "description": "Gestión de **proyectos**. Un proyecto agrupa varias tareas."},
    {"name": "tasks", "description": "Gestión de **tareas**. Cada tarea pertenece a un proyecto (`project_id`)."},
]
