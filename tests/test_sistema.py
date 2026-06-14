"""
Suite de pruebas unitarias e integración del sistema de IA empresarial.

Ejecutar con:
    pytest tests/ -v --tb=short
"""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Aseguramos que el directorio raíz del proyecto esté en el path
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ===========================================================================
# PRUEBAS UNITARIAS — Módulo: adaptadores_mcp
# ===========================================================================
class TestMCPServer:
    """Valida que la lista de comandos permitidos se aplique correctamente."""

    def test_comando_permitido_restart(self):
        from adaptadores_mcp.mcp_server import ejecutar_comando_seguro
        result = ejecutar_comando_seguro("systemctl restart app")
        assert "Éxito" in result or "xito" in result  # tolera encoding

    def test_comando_permitido_status(self):
        from adaptadores_mcp.mcp_server import ejecutar_comando_seguro
        result = ejecutar_comando_seguro("systemctl status app")
        assert "Éxito" in result or "xito" in result

    def test_comando_denegado(self):
        from adaptadores_mcp.mcp_server import ejecutar_comando_seguro
        result = ejecutar_comando_seguro("rm -rf /")
        assert "denegado" in result.lower() or "seguridad" in result.lower()

    def test_comando_con_espacios_extra(self):
        """Verifica que un comando con espacios extra sea denegado por seguridad."""
        from adaptadores_mcp.mcp_server import ejecutar_comando_seguro
        result = ejecutar_comando_seguro("  rm -rf /  ")
        assert "denegado" in result.lower() or "seguridad" in result.lower()


# ===========================================================================
# PRUEBAS UNITARIAS — Módulo: ranking
# ===========================================================================
class TestDocumentReranker:
    """Valida el reordenamiento semántico de documentos."""

    @pytest.fixture(autouse=True)
    def reranker(self):
        from ranking.reranker import DocumentReranker
        self.reranker = DocumentReranker()

    def _make_docs(self, texts: list):
        """Crea objetos Document mock con page_content y metadata."""
        docs = []
        for t in texts:
            doc = MagicMock()
            doc.page_content = t
            doc.metadata = {}
            docs.append(doc)
        return docs

    def test_rerank_vacio_devuelve_lista_vacia(self):
        result = self.reranker.rerank("consulta", [])
        assert result == []

    def test_rerank_agrega_score(self):
        docs = self._make_docs(["El error 5002 es un timeout.", "Los reembolsos tardan 3 días."])
        ranked = self.reranker.rerank("¿qué es el error 5002?", docs)
        assert all("score" in d.metadata for d in ranked)

    def test_rerank_ordena_por_relevancia(self):
        docs = self._make_docs([
            "El clima hoy es soleado.",
            "El error 5002 ocurre cuando hay un timeout en la base de datos.",
        ])
        ranked = self.reranker.rerank("error 5002", docs)
        # El documento sobre el error debe quedar primero
        assert "5002" in ranked[0].page_content or "timeout" in ranked[0].page_content

    def test_rerank_mantiene_todos_los_documentos(self):
        texts = ["doc A", "doc B", "doc C"]
        docs = self._make_docs(texts)
        ranked = self.reranker.rerank("consulta", docs)
        assert len(ranked) == len(texts)


# ===========================================================================
# PRUEBAS UNITARIAS — Módulo: retrieval
# ===========================================================================
class TestKnowledgeBase:
    """Valida la carga y búsqueda en la base de datos vectorial."""

    @pytest.fixture(autouse=True)
    def kb(self):
        from retrieval.vector_store import KnowledgeBase
        self.kb = KnowledgeBase()
        self.kb.data_seed()

    def test_busqueda_devuelve_resultados(self):
        results = self.kb.search("reembolso", k=2)
        assert len(results) > 0

    def test_busqueda_relevante_reembolso(self):
        results = self.kb.search("¿cuánto tiempo tarda un reembolso?", k=1)
        assert any("reembolso" in r.page_content.lower() or "días" in r.page_content for r in results)

    def test_busqueda_relevante_error(self):
        results = self.kb.search("error 5002 timeout", k=1)
        assert any("5002" in r.page_content or "timeout" in r.page_content.lower() for r in results)

    def test_busqueda_k_limita_resultados(self):
        results = self.kb.search("servidor", k=1)
        assert len(results) <= 1


# ===========================================================================
# PRUEBAS UNITARIAS — Módulo: observabilidad
# ===========================================================================
class TestMonitor:
    """Valida el decorador de métricas."""

    def test_decorador_no_interrumpe_funcion_exitosa(self):
        from observabilidad.monitor import medir_metricas_criticas

        @medir_metricas_criticas
        def funcion_ok():
            return 42

        assert funcion_ok() == 42

    def test_decorador_propaga_excepcion(self):
        from observabilidad.monitor import medir_metricas_criticas

        @medir_metricas_criticas
        def funcion_falla():
            raise ValueError("Error intencional de prueba")

        with pytest.raises(ValueError, match="Error intencional"):
            funcion_falla()

    def test_instrumentar_setea_variables_de_entorno(self, monkeypatch):
        from observabilidad.monitor import instrumentar_vias_produccion
        monkeypatch.setenv("LANGCHAIN_API_KEY", "test-key")
        instrumentar_vias_produccion()
        assert os.environ.get("LANGCHAIN_TRACING_V2") == "true"
        assert os.environ.get("LANGCHAIN_PROJECT") == "IA-Production-Enterprise-Agent"


# ===========================================================================
# PRUEBAS DE INTEGRACIÓN — Flujo RAG completo (con LLM mockeado)
# ===========================================================================
class TestAgentGraphIntegration:
    """
    Valida el flujo completo del grafo de agente sin llamar a APIs externas.
    El LLM se mockea para garantizar tests deterministas y sin costo.
    """

    @pytest.fixture(autouse=True)
    def mock_llm(self):
        """Reemplaza la llamada real al LLM con una respuesta fija."""
        mock_response = MagicMock()
        mock_response.content = "Los reembolsos tardan entre 3 y 5 días hábiles."
        with patch("agente.graph._llm") as mock:
            mock.invoke.return_value = mock_response
            yield mock

    def test_flujo_rag_puro(self):
        """Verifica que una consulta RAG devuelva una respuesta coherente."""
        from agente.graph import app_agente
        estado = {
            "query": "¿Cuánto demora un reembolso?",
            "contexto_recuperado": [],
            "herramienta_requerida": "",
            "respuesta_final": "",
            "iteraciones": 0,
        }
        resultado = app_agente.invoke(estado)
        assert isinstance(resultado["respuesta_final"], str)
        assert len(resultado["respuesta_final"]) > 0

    def test_flujo_mcp_reiniciar_servidor(self):
        """Verifica que una query de reinicio sea enrutada al nodo MCP."""
        from agente.graph import app_agente
        estado = {
            "query": "necesito reiniciar el servidor ahora",
            "contexto_recuperado": [],
            "herramienta_requerida": "",
            "respuesta_final": "",
            "iteraciones": 0,
        }
        resultado = app_agente.invoke(estado)
        assert "MCP" in resultado["respuesta_final"] or "comando" in resultado["respuesta_final"].lower()

    def test_contador_iteraciones_incrementa(self):
        """Verifica que el estado lleve cuenta de las iteraciones."""
        from agente.graph import app_agente
        estado = {
            "query": "¿Qué es el error 5002?",
            "contexto_recuperado": [],
            "herramienta_requerida": "",
            "respuesta_final": "",
            "iteraciones": 0,
        }
        resultado = app_agente.invoke(estado)
        assert resultado["iteraciones"] >= 1


# ===========================================================================
# PRUEBAS DE INTEGRACIÓN — API REST
# ===========================================================================
class TestAPIEndpoints:
    """Valida los endpoints HTTP de la aplicación FastAPI."""

    @pytest.fixture(autouse=True)
    def client(self):
        from fastapi.testclient import TestClient
        from api.main import app
        self.client = TestClient(app, raise_server_exceptions=False)

    def test_health_retorna_ok(self):
        response = self.client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_query_vacia_retorna_400(self):
        response = self.client.post("/query", json={"pregunta": "   "})
        assert response.status_code == 400

    @patch("orquestacion.pipeline.ejecutar_pipeline_empresarial", return_value="Respuesta mock")
    def test_query_valida_retorna_200(self, mock_pipeline):
        os.environ["OPENAI_API_KEY"] = "test-key"
        response = self.client.post("/query", json={"pregunta": "¿Cuánto demora un reembolso?"})
        assert response.status_code == 200
        data = response.json()
        assert "respuesta" in data
        assert "latencia_s" in data

    def test_ready_sin_api_key_retorna_503(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        response = self.client.get("/ready")
        assert response.status_code == 503
