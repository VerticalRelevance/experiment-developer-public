from abc import ABC, abstractmethod
from typing import List, Optional
from pathlib import Path

class StorageProvider(ABC):
    """Abstract base class for storage providers."""
    
    @abstractmethod
    def download_directory(self, source: str, destination: Path) -> None:
        """Download a directory from storage."""
        pass
    
    @abstractmethod
    def upload_directory(self, source: Path, destination: str) -> None:
        """Upload a directory to storage."""
        pass
    
    @abstractmethod
    def delete_directory(self, path: str) -> None:
        """Delete a directory from storage."""
        pass
    
    @abstractmethod
    def delete_files(self, files: List[str]) -> None:
        """Delete specific files from storage."""
        pass
    
    @abstractmethod
    def list_files(self, directory: str, pattern: Optional[str] = None) -> List[str]:
        """List files in a directory, optionally filtered by pattern."""
        pass
