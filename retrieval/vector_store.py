import chromadb
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings

class KnowledgeBase:
    def __init__(self):
        # Usamos un modelo de embeddings ligero y eficiente para producción
        self.embeddings = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
        # Inicializamos base de datos vectorial en memoria/local
        self.chroma_client = chromadb.Client()
        self.vector_store = Chroma(
            client=self.chroma_client,
            collection_name="knowledge_base",
            embedding_function=self.embeddings
        )

    def data_seed(self):
        """Simula la carga de conocimiento interno de la empresa."""
        texts = [
            "El error 5002 en el sistema se debe a una falla de timeout en la base de datos de clientes.",
            "Para reiniciar el servidor de aplicaciones, se debe ejecutar el comando: systemctl restart app.",
            "Los reembolsos de dinero tardan entre 3 a 5 días hábiles en procesarse legalmente."
        ]
        self.vector_store.add_texts(texts=texts)

    def search(self, query: str, k: int = 3):
        """Busca los documentos más relevantes."""
        return self.vector_store.similarity_search(query, k=k)