from abc import ABC, abstractmethod
from typing import List, Dict, Any

class FilePreprocessor(ABC):

    @abstractmethod
    def process_file(self, file_path: str, **kwargs):
        pass

    def process_list_of_files(self, list_of_paths: list[str], **kwargs):
        processed_files = []
        for path in list_of_paths:
            processed_files.extend(self.process_file(path, **kwargs))
        return processed_files
