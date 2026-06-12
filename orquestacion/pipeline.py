from agente.graph import app_agente
from observabilidad.monitor import instrumentar_vias_produccion

def ejecutar_pipeline_empresarial(pregunta_usuario: str):
    print(f"\n=== PROCESANDO NUEVA CONSULTA EN PRODUCCIÓN: '{pregunta_usuario}' ===")
    
    # Activamos telemetría
    instrumentar_vias_produccion()
    
    # Inicializamos estado limpio
    estado_inicial = {
        "query": pregunta_usuario,
        "contexto_recuperado": [],
        "herramienta_requerida": "",
        "respuesta_final": "",
        "iteraciones": 0
    }
    
    # Corre el grafo de forma síncrona
    resultado = app_agente.invoke(estado_inicial)
    
    print("\n================== RESPUESTA FINAL =================")
    print(resultado["respuesta_final"])
    print("====================================================")

if __name__ == "__main__":
    # Caso de Prueba 1: Flujo RAG Puro
    ejecutar_pipeline_empresarial("¿Cuánto demora en impactar un reembolso?")
    
    # Caso de Prueba 2: Flujo con herramientas críticas de infraestructura (Enrutado a MCP seguro)
    ejecutar_pipeline_empresarial("Por favor necesito reiniciar el servidor de inmediato")