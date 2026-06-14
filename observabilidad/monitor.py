import os
import time
from functools import wraps
from langsmith import Client as LangSmithClient

# ------------------------------------------------------------------
# Configuración de trazabilidad: las credenciales se leen desde el
# entorno, NUNCA se hardcodean en el código fuente.
# ------------------------------------------------------------------
def instrumentar_vias_produccion():
    """Configura el SDK de LangSmith para captura automática de trazas."""
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_PROJECT", "IA-Production-Enterprise-Agent")
    # LANGCHAIN_API_KEY debe estar en el entorno (via Secret de K8s o .env local)
    if not os.environ.get("LANGCHAIN_API_KEY"):
        print("[TELEMETRÍA] ADVERTENCIA: LANGCHAIN_API_KEY no configurada. "
              "Las trazas no se exportarán a LangSmith.")

# Instancia compartida del cliente LangSmith (se inicializa una sola vez)
_langsmith_client: LangSmithClient | None = None

def _get_langsmith_client() -> LangSmithClient | None:
    global _langsmith_client
    if _langsmith_client is None and os.environ.get("LANGCHAIN_API_KEY"):
        try:
            _langsmith_client = LangSmithClient()
        except Exception:
            pass  # Sin credenciales, operamos en modo silencioso
    return _langsmith_client


def medir_metricas_criticas(func):
    """Decorador que captura Latencia operativa y Errores,
    y los exporta a LangSmith cuando las credenciales están disponibles."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        inicio = time.time()
        estatus = "SUCCESS"
        error_msg = None
        try:
            resultado = func(*args, **kwargs)
            return resultado
        except Exception as e:
            estatus = "ERROR"
            error_msg = str(e)
            raise
        finally:
            latencia = time.time() - inicio
            print(
                f"\n[TELEMETRÍA] Función: {func.__name__} | "
                f"Latencia: {latencia:.4f}s | Estatus: {estatus}"
                + (f" | Error: {error_msg}" if error_msg else "")
            )
            # Exportación real de métricas a LangSmith
            client = _get_langsmith_client()
            if client:
                try:
                    client.create_run(
                        name=func.__name__,
                        run_type="chain",
                        inputs={"args_count": len(args)},
                        outputs={"status": estatus, "latency_s": round(latencia, 4)},
                        error=error_msg,
                        project_name=os.environ.get(
                            "LANGCHAIN_PROJECT", "IA-Production-Enterprise-Agent"
                        ),
                    )
                except Exception:
                    pass  # El fallo de telemetría no debe interrumpir el sistema
    return wrapper