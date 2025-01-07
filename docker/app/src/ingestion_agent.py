import logging
from pathlib import Path
from typing import List, Optional

from src.config.model_manager import ModelManager
from src.preprocessors import PythonPreprocessor
from src.chroma_interface import ExperimentVrClient
from src.services.storage import S3StorageProvider
from src.config.settings import Settings

logger = logging.getLogger(__name__)

class IngestionAgent:
    """Agent responsible for ingesting and processing files."""
    
    def __init__(self) -> None:
        self.settings = Settings.get_settings()
        self.models = ModelManager.get_instance()
        self.storage = S3StorageProvider()
        self.preprocessor = PythonPreprocessor()
        self.chroma_client: Optional[ExperimentVrClient] = None
        self.tmp_path = Path("./tmp")

    def ingest(self) -> None:
        """Ingest files from storage into ChromaDB."""
        try:
            logger.info("Starting ingestion process...")
            self._initialize_chroma_db()
            uningested_files = self._download_uningested_files()
            self._process_and_embed_files(uningested_files)
            self._finalize_ingestion()
            logger.info("Ingestion process completed successfully")
        except Exception as e:
            logger.error(f"Ingestion process failed: {str(e)}")
            raise

    def _initialize_chroma_db(self) -> None:
        """Initialize ChromaDB connection."""
        logger.info("Getting current Chroma DB...")
        self.chroma_client = self.get_current_chroma_db()

    def _download_uningested_files(self) -> Path:
        """Download files that need to be ingested."""
        logger.info("Getting uningested files...")
        uningested_path = self.tmp_path / self.settings.storage.uningested_path
        
        try:
            self.storage.download_directory(
                self.settings.storage.uningested_path,
                uningested_path
            )
            return uningested_path
        except Exception as e:
            logger.error(f"Failed to download uningested files: {str(e)}")
            raise

    def _process_and_embed_files(self, uningested_path: Path) -> None:
        """Process and embed files into ChromaDB."""
        if not self.chroma_client:
            raise RuntimeError("ChromaDB client not initialized")

        python_files = self._get_python_files(uningested_path)
        if not python_files:
            logger.info("No Python files found for processing")
            return

        try:
            results_to_embed = self.preprocessor.process_list_of_files(
                python_files,
                summarize=self.settings.model.embedding_summarize
            )
            
            if results_to_embed:
                logger.info(f"Embedding {len(results_to_embed)} document(s) into local Chroma DB...")
                self.chroma_client.upsert_docs_with_id(docs=results_to_embed)
        except Exception as e:
            logger.error(f"Failed to process or embed files: {str(e)}")
            raise

    def _finalize_ingestion(self) -> None:
        """Upload processed files and clean up."""
        try:
            self.storage.upload_directory(
                self.tmp_path / self.settings.storage.db_path,
                self.settings.storage.db_path
            )
            self.storage.delete_directory(self.settings.storage.uningested_path)
        except Exception as e:
            logger.error(f"Failed to finalize ingestion: {str(e)}")
            raise

    def get_current_chroma_db(self) -> ExperimentVrClient:
        """Get or create ChromaDB client with current data."""
        try:
            db_path = self.settings.storage.db_path
            self.storage.download_directory(
                db_path,
                f"./tmp/{db_path}"
            )
            return ExperimentVrClient(embedding_function=self.models.provision_embeddings())
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {str(e)}")
            raise

    def _get_python_files(self, directory: Path) -> List[str]:
        """Get list of Python files in directory."""
        return [
            str(file) for file in directory.rglob("*.py")
            if file.is_file()
        ]
