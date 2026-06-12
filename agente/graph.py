from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
from retrieval.vector_store import KnowledgeBase
from ranking.reranker import DocumentReranker
from adaptadores_mcp.mcp_server import ejecutar_comando_seguro
from observabilidad.monitor import medir_metricas_criticas

# 1. Definimos el Estado del Agente
class AgenteState(TypedDict):
    query: str
    contexto_recuperado: List[str]
    herramienta_requerida: str
    respuesta_final: str
    iteraciones: int

# Inicializamos módulos internos
kb = KnowledgeBase()
kb.data_seed()
reranker = DocumentReranker()

# 2. Definición de Nodos del Grafo
@medir_metricas_criticas
def nodo_recuperar_rag(state: AgenteState) -> Dict[str, Any]:
    print("-> Nodo: Recuperando de base de datos vectorial")
    docs = kb.search(state["query"])
    docs_filtrados = reranker.rerank(state["query"], docs)
    textos = [d.page_content for d in docs_filtrados]
    return {"contexto_recuperado": textos, "iteraciones": state.get("iteraciones", 0) + 1}

@medir_metricas_criticas
def nodo_analizar_herramientas(state: AgenteState) -> Dict[str, Any]:
    print("-> Nodo: Analizando si requiere ejecución externa (MCP)")
    # Simulación de razonamiento del LLM decidiendo usar una herramienta de sistema
    if "reiniciar" in state["query"] or "systemctl" in state["query"]:
        return {"herramienta_requerida": "ejecutar_comando_seguro"}
    return {"herramienta_requerida": "ninguna"}

@medir_metricas_criticas
def nodo_ejecutar_mcp(state: AgenteState) -> Dict[str, Any]:
    print("-> Nodo: Ejecutando acción segura vía protocolo MCP")
    # Extraemos el comando implícito de la query
    comando = "systemctl restart app" if "reiniciar" in state["query"] else "invalido"
    resultado_mcp = ejecutar_comando_seguro(comando)
    return {"respuesta_final": f"Acción realizada. Reporte MCP: {resultado_mcp}"}

@medir_metricas_criticas
def nodo_generar_respuesta(state: AgenteState) -> Dict[str, Any]:
    print("-> Nodo: Sintetizando respuesta al usuario")
    contexto = " ".join(state["contexto_recuperado"])
    respuesta = f"Basado en el contexto interno corporativo: {contexto}"
    return {"respuesta_final": respuesta}

# 3. Construcción del Flujo Líclico (Grafo)
workflow = StateGraph(AgenteState)

# Registrar Nodos
workflow.add_node("recuperar_rag", nodo_recuperar_rag)
workflow.add_node("analizar_herramientas", nodo_analizar_herramientas)
workflow.add_node("ejecutar_mcp", nodo_ejecutar_mcp)
workflow.add_node("generar_respuesta", nodo_generar_respuesta)

# Definir el Flujo de Entrada
workflow.set_entry_point("recuperar_rag")
workflow.add_edge("recuperar_rag", "analizar_herramientas")

# Enrutador Condicional (Decisión dinámica basada en el Estado)
def enrutador_logico(state: AgenteState):
    if state["herramienta_requerida"] == "ejecutar_comando_seguro":
        return "ejecutar_mcp"
    return "generar_respuesta"

workflow.add_conditional_edges(
    "analizar_herramientas",
    enrutador_logico,
    {
        "ejecutar_mcp": "ejecutar_mcp",
        "generar_respuesta": "generar_respuesta"
    }
)

workflow.add_edge("ejecutar_mcp", END)
workflow.add_edge("generar_respuesta", END)

# Compilamos el sistema orquestado
app_agente = workflow.compile()