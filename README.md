# IA Production System

Este proyecto es un sistema de producción basado en Inteligencia Artificial que implementa flujos de Recuperación Generativa Aumentada (RAG) y Agentes inteligentes utilizando arquitecturas modernas y escalables.

## Estructura del Proyecto

A continuación se detalla la estructura de directorios y componentes principales del sistema:

```text
ia-production-system/
│
├── retrieval/                # Componente de recuperación de información
│   ├── __init__.py
│   └── vector_store.py       # Gestión del almacén de vectores (Vector Store)
│
├── ranking/                  # Reordenamiento de documentos (Reranking)
│   ├── __init__.py
│   └── reranker.py           # Algoritmos de reranking para mejorar la relevancia
│
├── orquestacion/             # Control y flujo de trabajo principal
│   ├── __init__.py
│   └── pipeline.py           # Tubería de orquestación de datos y peticiones
│
├── agente/                   # Definición de agentes y lógica de decisión
│   ├── __init__.py
│   └── graph.py              # Implementación del grafo de agente (e.g., LangGraph)
│
├── adaptadores_mcp/          # Protocolo de Contexto de Modelo (MCP)
│   ├── __init__.py
│   └── mcp_server.py         # Servidor MCP para exposición de herramientas/recursos
│
├── observabilidad/           # Monitoreo, trazabilidad y telemetría
│   ├── __init__.py
│   └── monitor.py            # Registro de latencias, logs y telemetría general
│
├── despliegue/               # Archivos de configuración para infraestructura
│   ├── deployment.yaml       # Configuración del Deployment de Kubernetes
│   └── service.yaml          # Configuración del Servicio de Kubernetes
│
├── requirements.txt          # Dependencias y requerimientos del proyecto
└── README.md                 # Documentación del sistema (este archivo)
```

## Componentes Clave

*   **`retrieval`**: Permite interactuar con bases de datos vectoriales para almacenar y recuperar fragmentos de documentos relevantes de forma semántica.
*   **`ranking`**: Optimiza los resultados de búsqueda de vectores utilizando modelos de reranking (como Cohere u otros), reduciendo el ruido en el contexto entregado al modelo de lenguaje.
*   **`orquestacion`**: Define el flujo principal en el que las peticiones se procesan secuencialmente.
*   **`agente`**: Implementa la lógica basada en grafos para agentes conversacionales autónomos que pueden razonar y tomar decisiones.
*   **`adaptadores_mcp`**: Implementación de servidores basados en **Model Context Protocol (MCP)** para habilitar la integración del sistema con clientes MCP y orquestadores externos.
*   **`observabilidad`**: Seguimiento e instrumentación detallada de las latencias de procesamiento de cada componente para el diagnóstico y optimización en producción.
*   **`despliegue`**: Manifiestos de Kubernetes listos para empaquetar la aplicación en un contenedor de Docker e implementarla en un clúster productivo.

# Sistema de Agente de IA para Entornos Empresariales Robustos

Este repositorio contiene la arquitectura de producción de un sistema de IA de grado empresarial que integra patrones avanzados de recuperación, orquestación cíclica y seguridad de ejecución.

## 🏗️ Decisiones Arquitectónicas Justificadas

1. **RAG con Re-ranking Bifásico**: Se implementó una base de datos vectorial local (ChromaDB) acoplada a un modelo Cross-Encoder (`ms-marco-MiniLM`). Esto mitiga el problema de la pérdida de contexto en ventanas grandes y optimiza los costos de inferencia al procesar solo fragmentos con alto grado de relevancia semántica real.
2. **Orquestación de Estado con LangGraph**: A diferencia de las cadenas lineales tradicionales de LangChain, LangGraph permite modelar el sistema como un Grafo de Estados Dirigido (DAG). Esto habilita razonamientos cíclicos y comportamientos reactivos iterativos, fundamentales para sistemas de autoevaluación (Self-RAG).
3. **Model Context Protocol (MCP)**: Las interacciones del agente con herramientas críticas del sistema operativo se delegaron de forma estricta bajo la especificación MCP de Anthropic, aislando los efectos secundarios del LLM mediante comunicación estándar por pipes (stdin/stdout), impidiendo ataques de inyección de prompts que comprometan la infraestructura.

## 📊 Matriz de Métricas de Observabilidad Instrumentadas

* **Latencia Operativa de Nodos**: Medida mediante decoradores de tiempo en cada subproceso crítico del grafo para detectar cuellos de botella en la fase de embedding frente a la inferencia.
* **Tasa de Ejecución Segura (MCP Compliance)**: Monitoreo estricto sobre comandos interceptados vs. comandos permitidos para auditorías de seguridad perimetral.
* **Trazabilidad Completa (LangSmith)**: Instrumentación transparente mediante variables nativas del SDK para inspeccionar el árbol de llamadas e insumos intermedios de los prompts.

## 🚀 Guía de Despliegue en Producción

Para desplegar los microservicios de manera resiliente dentro del clúster de Kubernetes corporativo, ejecute:

```bash
kubectl apply -f despliegue/deployment.yaml

## Requisitos de Instalación

Las dependencias principales comentadas en el proyecto incluyen:
*   `langchain`
*   `langgraph`
*   `fastapi`
*   `uvicorn`
*   `pydantic`
*   `numpy`
*   `openai`

Para instalar y comenzar a desarrollar localmente, puedes descomentar los paquetes requeridos en `requirements.txt` y ejecutar:

```bash
pip install -r requirements.txt
```
