"""
API REST del sistema de IA empresarial.

Expone el pipeline del agente a través de HTTP y provee
los endpoints de salud requeridos por Kubernetes.
"""

import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from observabilidad.monitor import instrumentar_vias_produccion


# ---------------------------------------------------------------------------
# Ciclo de vida de la aplicación
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa la telemetría al arrancar; libera recursos al cerrar."""
    instrumentar_vias_produccion()
    # Importación lazy para evitar inicializar modelos pesados antes de tiempo
    from orquestacion.pipeline import ejecutar_pipeline_empresarial
    app.state.pipeline = ejecutar_pipeline_empresarial
    app.state.start_time = time.time()
    yield
    # Teardown (si hubiera conexiones persistentes, se cerrarían aquí)


app = FastAPI(
    title="IA Production Enterprise Agent",
    description=(
        "Sistema de agente empresarial con RAG bifásico, "
        "integración MCP y trazabilidad completa via LangSmith."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Modelos de datos
# ---------------------------------------------------------------------------
class QueryRequest(BaseModel):
    pregunta: str


class QueryResponse(BaseModel):
    respuesta: str
    latencia_s: float


# ---------------------------------------------------------------------------
# Endpoints de negocio
# ---------------------------------------------------------------------------
@app.post("/query", response_model=QueryResponse, summary="Consulta al agente de IA")
async def query_agent(body: QueryRequest):
    """Procesa una pregunta a través del pipeline RAG + LLM y devuelve la respuesta."""
    if not body.pregunta.strip():
        raise HTTPException(status_code=400, detail="La pregunta no puede estar vacía.")

    inicio = time.time()
    try:
        from orquestacion.pipeline import ejecutar_pipeline_empresarial
        respuesta = ejecutar_pipeline_empresarial(body.pregunta)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error interno del agente: {exc}")

    latencia = round(time.time() - inicio, 4)
    return QueryResponse(respuesta=respuesta, latencia_s=latencia)


# ---------------------------------------------------------------------------
# Endpoints de salud (requeridos por Kubernetes liveness / readiness probes)
# ---------------------------------------------------------------------------
@app.get("/health", summary="Liveness probe")
async def health():
    """Indica que el proceso está vivo. K8s reinicia el pod si falla."""
    return {"status": "ok"}


@app.get("/ready", summary="Readiness probe")
async def ready():
    """
    Indica que la aplicación está lista para recibir tráfico.
    Verifica que las variables de entorno críticas estén presentes.
    """
    missing = [v for v in ["OPENAI_API_KEY"] if not os.environ.get(v)]
    if missing:
        raise HTTPException(
            status_code=503,
            detail=f"Variables de entorno faltantes: {missing}",
        )
    return {"status": "ready", "uptime_s": round(time.time() - app.state.start_time, 1)}
