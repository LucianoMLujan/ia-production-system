import os
import time
from functools import wraps

def instrumentar_vias_produccion():
    """Configura las variables globales para que LangSmith capture trazas automáticamente."""
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    # Reemplazar con credenciales reales en producción
    os.environ["LANGCHAIN_API_KEY"] = "ls__mock_key_para_entrega_final_generica"
    os.environ["LANGCHAIN_PROJECT"] = "IA-Production-Enterprise-Agent"

def medir_metricas_criticas(func):
    """Decorador personalizado para capturar Latencia operativa y Erreores."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        inicio = time.time()
        try:
            resultado = func(*args, **kwargs)
            latencia = time.time() - inicio
            # Aquí se enviarían las métricas a Arize / LangSmith
            print(f"\n[TELEMETRÍA] Función: {func.__name__} | Latencia: {latencia:.4f}s | Estatus: SUCCESS")
            return resultado
        except Exception as e:
            latencia = time.time() - inicio
            print(f"\n[TELEMETRÍA ALERT] Función: {func.__name__} | Latencia: {latencia:.4f}s | Error: {str(e)}")
            raise e
    return wrapper