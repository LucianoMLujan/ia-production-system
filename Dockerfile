# syntax=docker/dockerfile:1
# ─────────────────────────────────────────────────────────────────────────────
# Etapa 1 — Builder: instala dependencias en un entorno limpio
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Instalar dependencias del sistema necesarias para sentence-transformers y chromadb
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar solo requirements primero para aprovechar el cache de capas de Docker
COPY requirements.txt .

# Instalar en un directorio separado para copiarlo en la etapa final
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ─────────────────────────────────────────────────────────────────────────────
# Etapa 2 — Runtime: imagen mínima de producción
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Metadatos del contenedor
LABEL maintainer="equipo-ia@empresa.com"
LABEL description="IA Production Enterprise Agent — RAG + LangGraph + MCP"
LABEL version="1.0.0"

WORKDIR /app

# Copiar dependencias instaladas desde el builder
COPY --from=builder /install /usr/local

# Copiar el código fuente de la aplicación
COPY agente/          ./agente/
COPY adaptadores_mcp/ ./adaptadores_mcp/
COPY api/             ./api/
COPY observabilidad/  ./observabilidad/
COPY orquestacion/    ./orquestacion/
COPY ranking/         ./ranking/
COPY retrieval/       ./retrieval/

# Crear usuario no-root por seguridad (principio de mínimo privilegio)
RUN useradd --no-create-home --shell /bin/false agentuser
USER agentuser

# Variables de entorno de producción (los secrets se inyectan en runtime via K8s)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LANGCHAIN_TRACING_V2=true \
    LANGCHAIN_PROJECT=IA-Production-Enterprise-Agent

# Puerto expuesto por la API REST (FastAPI + Uvicorn)
EXPOSE 8000

# Healthcheck nativo de Docker: consulta el endpoint /health cada 30s
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" \
    || exit 1

# Comando de inicio con workers ajustados para producción
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
