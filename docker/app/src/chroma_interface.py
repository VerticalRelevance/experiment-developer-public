import logging
from langchain_core.embeddings import Embeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from src.config.model_manager import ModelManager
from src.config.settings import Settings

logger = logging.getLogger(__name__)

 
class CodebaseChroma(Chroma):
    collection_name = "default"

    def __init__(
        self,
        persist_directory: str = None,
        embedding_function: Embeddings = None,
    ):
        settings = Settings.get_settings()
        persist_directory = (
            persist_directory if persist_directory else settings.storage.persist_directory
        )
        embedding_function = (
            embedding_function if embedding_function else ModelManager.get_instance().embeddings
        )

        super().__init__(
            persist_directory=persist_directory,
            embedding_function=embedding_function,
            collection_name=self.collection_name,
        )

    def upsert_docs_with_id(self, docs: list[Document], id_var: str = "path"):
        texts, metadatas, ids = [], [], []
        for doc in docs:
            texts.append(doc.page_content)
            metadatas.append(doc.metadata)
            ids.append(doc.metadata[id_var])

        self.add_texts(texts, metadatas, ids)


class ExperimentVrClient(CodebaseChroma):
    collection_name = "experimentvr"
