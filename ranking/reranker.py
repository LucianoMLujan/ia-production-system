from sentence_transformers import CrossEncoder

class DocumentReranker:
    def __init__(self):
        # Un modelo Cross-Encoder es ideal para scoring de relevancia
        self.model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

    def rerank(self, query: str, documents: list) -> list:
        """Reordena los documentos de mayor a menor relevancia técnica."""
        if not documents:
            return []
        
        # Prepara los pares (Query, Documento)
        pairs = [[query, doc.page_content] for doc in documents]
        scores = self.model.predict(pairs)
        
        # Añade el score al objeto del documento y los ordena
        for i, doc in enumerate(documents):
            doc.metadata["score"] = float(scores[i])
            
        ranked_docs = sorted(documents, key=lambda x: x.metadata["score"], reverse=True)
        return ranked_docs