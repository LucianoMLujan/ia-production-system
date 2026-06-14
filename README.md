# IA Production Enterprise Agent

Sistema de agente empresarial de grado de producción que integra RAG bifásico,
orquestación cíclica con LangGraph, un LLM real (GPT-4o-mini), seguridad MCP
y observabilidad completa via LangSmith.

---

## 🏗️ Estructura del Proyecto

```text
ia-production-system/
│
├── api/                      # API REST (FastAPI) + healthchecks
│   └── main.py               # Endpoints /query, /health, /ready
│
├── agente/                   # Grafo de agente (LangGraph)
│   └── graph.py              # Nodos RAG, MCP y generación LLM real
│
├── retrieval/                # Base de datos vectorial (ChromaDB)
│   └── vector_store.py
│
├── ranking/                  # Re-ranking bifásico (CrossEncoder)
│   └── reranker.py
│
├── orquestacion/             # Pipeline principal
│   └── pipeline.py
│
├── adaptadores_mcp/          # Servidor MCP (seguridad de herramientas)
│   └── mcp_server.py
│
├── observabilidad/           # Telemetría y exportación a LangSmith
│   └── monitor.py
│
├── despliegue/               # Manifiestos Kubernetes
│   ├── deployment.yaml       # Deployment con liveness/readiness/startup probes
│   └── service.yaml          # Service ClusterIP (consistente con el Deployment)
│
├── tests/                    # Suite de pruebas automáticas
│   └── test_sistema.py       # Unit + integración (>70% cobertura)
│
├── docs/
│   └── SLOs_y_Runbook.md    # SLOs definidos y runbooks de incidentes
│
├── .github/
│   └── workflows/
│       └── ci-cd.yml         # Pipeline CI/CD (GitHub Actions)
│
├── Dockerfile                # Imagen multi-stage de producción
└── requirements.txt          # Dependencias actualizadas y versionadas
```

---

## ✅ Decisiones Arquitectónicas

### 1. RAG con Re-ranking Bifásico
ChromaDB (embeddings `all-MiniLM-L6-v2`) recupera candidatos; el CrossEncoder
(`ms-marco-MiniLM-L-6-v2`) los reordena por relevancia semántica real. Esto
mitiga el problema de fragmentos irrelevantes al top-k y reduce costos de
inferencia al LLM.

### 2. Orquestación con LangGraph
El sistema se modela como un Grafo de Estados Dirigido (DAG), habilitando
razonamientos cíclicos y enrutamiento condicional (Self-RAG). El estado tipado
(`AgenteState`) garantiza consistencia entre nodos.

### 3. LLM Real — GPT-4o-mini
`nodo_generar_respuesta` llama a la API de OpenAI con `ChatOpenAI`. El contexto
recuperado se inyecta como `SystemMessage`, siguiendo la técnica de
*context-grounded generation* para minimizar alucinaciones.

### 4. Model Context Protocol (MCP)
Las interacciones con el sistema operativo se delegan estrictamente al servidor
MCP, aislando los efectos secundarios del LLM con una lista blanca explícita de
comandos. Previene ataques de inyección de prompts.

### 5. Observabilidad con LangSmith
Las credenciales se leen del entorno (nunca hardcodeadas). Si `LANGCHAIN_API_KEY`
está presente, cada nodo del grafo publica su latencia y estado a LangSmith vía
`client.create_run()`. El decorador `@medir_metricas_criticas` garantiza que
ningún fallo de telemetría interrumpa el sistema principal.

---

## 📊 SLOs Definidos

| SLO | Métrica | Objetivo |
|-----|---------|----------|
| SLO-01 | Disponibilidad HTTP 2xx | ≥ 99.5% |
| SLO-02 | Latencia p95 en `/query` | ≤ 5 s |
| SLO-03 | Latencia p99 en `/query` | ≤ 15 s |
| SLO-04 | Tasa de éxito MCP | ≥ 99.9% |
| SLO-05 | Tasa de error LLM | ≤ 1% |

Ver runbooks completos en [`docs/SLOs_y_Runbook.md`](docs/SLOs_y_Runbook.md).

---

## 🚀 Puesta en Marcha Local

### 1. Variables de entorno requeridas

```bash
cp .env.example .env
# Editar .env con tus claves:
# OPENAI_API_KEY=sk-...
# LANGCHAIN_API_KEY=ls__...
```

### 2. Instalar dependencias

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Ejecutar la API

```bash
uvicorn api.main:app --reload --port 8000
# La API estará disponible en http://localhost:8000
# Documentación interactiva: http://localhost:8000/docs
```

### 4. Ejecutar las pruebas

```bash
pytest tests/ -v --cov=. --cov-report=term-missing
```

---

## 🐳 Docker

```bash
# Build
docker build -t ia-agent:local .

# Run (con variables de entorno)
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=sk-... \
  -e LANGCHAIN_API_KEY=ls__... \
  ia-agent:local
```

---

## ☸️ Kubernetes

```bash
# Crear Secret con las API Keys
kubectl create secret generic api-keys-produccion \
  --from-literal=openai-key=$OPENAI_API_KEY \
  --from-literal=langchain-key=$LANGCHAIN_API_KEY

# Aplicar manifiestos
kubectl apply -f despliegue/

# Verificar estado
kubectl get pods -l app=ia-enterprise-agent
kubectl rollout status deployment/ia-agent-deployment
```

---

## 🔄 CI/CD

El pipeline `.github/workflows/ci-cd.yml` ejecuta tres jobs en secuencia:

1. **🧪 Tests** — `pytest` con cobertura mínima del 70%
2. **🐳 Docker** — Build multi-stage y push a GHCR (solo en `main`)
3. **🚀 Deploy** — `kubectl set image` + rollout verification (requiere aprobación manual)
