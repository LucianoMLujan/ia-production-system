# SLOs y Runbook de Operaciones — IA Production Enterprise Agent

## 1. Definición de SLOs (Service Level Objectives)

Los SLOs definen los umbrales de calidad de servicio medibles y acordados con las partes interesadas.
Se miden en ventanas rodantes de **28 días**.

| ID | Métrica | Objetivo | Error Budget (28 días) |
|----|---------|----------|------------------------|
| SLO-01 | **Disponibilidad** — % de solicitudes HTTP 2xx | ≥ 99.5% | ~3.4 horas |
| SLO-02 | **Latencia p95** — tiempo de respuesta del endpoint `/query` | ≤ 5 segundos | — |
| SLO-03 | **Latencia p99** — tiempo de respuesta del endpoint `/query` | ≤ 15 segundos | — |
| SLO-04 | **Tasa de éxito MCP** — comandos ejecutados vs. bloqueados correctamente | ≥ 99.9% | — |
| SLO-05 | **Tasa de error LLM** — respuestas vacías o errores de la API de OpenAI | ≤ 1% | — |

### Indicadores (SLIs) asociados

- **SLO-01**: `sum(rate(http_requests_total{status=~"2.."}[5m])) / sum(rate(http_requests_total[5m]))`
- **SLO-02/03**: Percentil de latencia medido por el decorador `medir_metricas_criticas` y exportado a LangSmith.
- **SLO-04**: Conteo de llamadas a `ejecutar_comando_seguro` con resultado `"Éxito"` vs. total.
- **SLO-05**: Conteo de excepciones capturadas en `nodo_generar_respuesta` / total de invocaciones.

---

## 2. Runbook de Situaciones de Falla

### 🔴 INCIDENTE-01 — Pod en estado `CrashLoopBackOff`

**Síntoma**: `kubectl get pods` muestra `CrashLoopBackOff` en uno o más pods.

**Diagnóstico**:
```bash
# Ver logs del pod fallido
kubectl logs -l app=ia-enterprise-agent --previous --tail=100

# Describir el pod para ver eventos y razón de falla
kubectl describe pod -l app=ia-enterprise-agent
```

**Causas comunes y solución**:

| Causa | Señal en logs | Solución |
|-------|--------------|----------|
| `OPENAI_API_KEY` ausente | `KeyError: OPENAI_API_KEY` | Verificar Secret K8s: `kubectl get secret api-keys-produccion -o yaml` |
| OOMKilled | `reason: OOMKilled` en `describe` | Aumentar `resources.limits.memory` en `deployment.yaml` |
| Timeout de modelos ML | `TimeoutError` en arranque | Aumentar `startupProbe.failureThreshold` o precargar modelos |
| Versión de imagen inválida | `ImagePullBackOff` | Verificar que el tag exista en el registry: `docker pull <imagen>` |

**Rollback rápido**:
```bash
kubectl rollout undo deployment/ia-agent-deployment
kubectl rollout status deployment/ia-agent-deployment
```

---

### 🟠 INCIDENTE-02 — SLO-01 violado (alta tasa de error 5xx)

**Síntoma**: El endpoint `/query` devuelve errores HTTP 500 de forma sostenida.

**Diagnóstico**:
```bash
# Ver logs en tiempo real de todos los pods
kubectl logs -f -l app=ia-enterprise-agent --all-containers

# Verificar el estado del deployment
kubectl get deployment ia-agent-deployment -o wide
```

**Árbol de decisión**:
1. ¿Los errores son `openai.RateLimitError`? → El proyecto consumió el límite de tokens. Esperar o escalar el plan de OpenAI.
2. ¿Los errores son de ChromaDB? → La colección en memoria fue perdida (el pod se reinició). Implementar persistencia con `chromadb.PersistentClient(path="/data/chroma")`.
3. ¿Los errores son de `sentence_transformers`? → El modelo no pudo descargarse. Verificar conectividad de red del pod.

**Mitigación inmediata**: Escalar a 0 réplicas y volver a escalar para forzar reinicio limpio:
```bash
kubectl scale deployment ia-agent-deployment --replicas=0
kubectl scale deployment ia-agent-deployment --replicas=3
```

---

### 🟡 INCIDENTE-03 — Latencia p95 superior al SLO (SLO-02 violado)

**Síntoma**: Las respuestas del endpoint `/query` superan los 5 segundos de forma consistente.

**Diagnóstico**: Revisar en LangSmith cuál nodo del grafo es el cuello de botella.

```bash
# Acceder al dashboard de LangSmith
open https://smith.langchain.com/projects
# Proyecto: IA-Production-Enterprise-Agent
# Filtrar por latencia decreciente
```

**Acciones por nodo lento**:

| Nodo lento | Causa probable | Solución |
|------------|---------------|----------|
| `nodo_recuperar_rag` | Embeddings lentos | Cachear embeddings de queries frecuentes |
| `nodo_recuperar_rag` → reranker | CrossEncoder es costoso | Reducir `k` de búsqueda o usar modelo de reranking más liviano |
| `nodo_generar_respuesta` | Latencia de API OpenAI | Activar `streaming=True` en el LLM para mejorar tiempo a primer token |

---

### 🔵 INCIDENTE-04 — Seguridad: Comando MCP denegado inesperadamente

**Síntoma**: El sistema deniega un comando que debería estar permitido.

**Diagnóstico**:
```bash
# Buscar en logs el mensaje de denegación
kubectl logs -l app=ia-enterprise-agent | grep "denegado por políticas"
```

**Solución**: Actualizar la lista `comandos_permitidos` en `adaptadores_mcp/mcp_server.py`, agregar el comando exacto (incluyendo espacios), y hacer un nuevo deploy.

> ⚠️ **NUNCA** agregar comandos genéricos con wildcards. Toda modificación requiere revisión por el equipo de seguridad.

---

## 3. Alertas recomendadas (Prometheus / LangSmith)

```yaml
# Ejemplo de alerta Prometheus (agregar a prometheus-rules.yaml)
groups:
  - name: ia-agent-slos
    rules:
      - alert: AltaTasaErrores
        expr: |
          sum(rate(http_requests_total{job="ia-agent",status=~"5.."}[5m]))
          / sum(rate(http_requests_total{job="ia-agent"}[5m])) > 0.005
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Tasa de error > 0.5% — SLO-01 en riesgo"

      - alert: LatenciaElevada
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{job="ia-agent"}[5m])) > 5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "p95 de latencia supera 5s — SLO-02 en riesgo"
```

---

## 4. Contactos de escalamiento

| Nivel | Responsable | Tiempo de respuesta |
|-------|-------------|---------------------|
| L1 — On-call | Equipo de Operaciones | 15 min |
| L2 — Ingeniería | Equipo de IA Backend | 1 hora |
| L3 — Proveedor | Soporte OpenAI | SLA del plan contratado |
