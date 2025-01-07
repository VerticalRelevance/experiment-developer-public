import ast, os, json
import logging
from typing import List, Dict, Any

from langchain_core.documents import Document
from langchain.prompts import PromptTemplate

from src.interfaces.file_preprocessor import FilePreprocessor
from src.models.func_description import FunctionDescription
from src.config.model_manager import ModelManager

logger = logging.getLogger(__name__)

class CodePreprocessor(FilePreprocessor):
    """Base preprocessor implementing common functionality for code files."""
    
    def summarize(self, content: str, file_type: str, path: str) -> Document:
        """Generate a summary of the content using the model."""
        logger.info(f"Summarizing {file_type} content...")
        
        model = ModelManager.get_instance().chat.with_structured_output(FunctionDescription)
        chain = self._create_summarize_prompt() | model
        
        response = chain.invoke({
            "lang": file_type,
            "func_json": json.dumps(content)
        })
        
        logger.info(f"Generated summary: {response}")
        return Document(
            page_content=response.summary,
            metadata={"path": path, "function_signature": response.function_signature}
        )
    
    def _create_summarize_prompt(self):
        """Get the prompt template for summarization."""
        template = """
        Your task is to provide a short concise summary of the {lang} function provided along with the name of the function and a list of arguments.

        Function
        {func_json}
        """
        return PromptTemplate(
            template=template,
            input_variables=["lang", "func_json"]
        )

class PythonPreprocessor(CodePreprocessor):
    """Preprocessor for Python files."""
    
    def process_file(self, file_path: str, summarize: bool, **kwargs):
        logger.info(f"Processing file: {file_path}")
        functions = self.split_file_by_functions(file_path)
        logger.info(f"Summarize: {summarize}")

        if summarize == True:
            return [
                self.summarize(code_str, file_type="python", path=func_path)
                for func_path, code_str in functions.items()
            ]
        return [
            Document(page_content=code_str, metadata={"path": func_path})
            for func_path, code_str in functions.items()
        ]

    def split_file_by_functions(
        self, file_path: str, remove_prefix: str = "tmp.uningested."
    ):
        logger.info("Splitting file by function.")
        with open(file_path, "r") as file:
            code = file.read()

        tree = ast.parse(code)

        functions = {}

        def get_code(node):
            return ast.get_source_segment(code, node)

        def get_path(node, current_path=file_path):
            if isinstance(node, ast.FunctionDef):
                return f"{current_path}.{node.name}" if current_path else node.name
            elif isinstance(node, ast.ClassDef):
                return f"{current_path}.{node.name}" if current_path else node.name
            return current_path

        def process_node(node, current_path=file_path):
            current_path = get_path(node, current_path)

            current_path = os.path.normpath(current_path).replace(os.path.sep, ".")
            current_path = current_path.removeprefix(remove_prefix)

            if isinstance(node, ast.FunctionDef):
                functions[current_path] = get_code(node)
            elif isinstance(node, ast.Module) or isinstance(node, ast.FunctionDef):
                for child_node in ast.iter_child_nodes(node):
                    process_node(child_node, current_path)

        process_node(tree)

        return functions

class CfnPreprocessor(CodePreprocessor):
    """Preprocessor for CloudFormation files."""
    
    def process_file(self, content: str, metadata: Dict[str, Any]) -> Document:
        """Process CloudFormation content."""
        pass

class WordPreprocessor(FilePreprocessor):
    """Preprocessor for Word files."""

    def process_file(self, content: str, metadata: Dict[str, Any]) -> Document:
        """Process Word content."""
        pass

if __name__ == "__main__":
    pyp = PythonPreprocessor()
    proc = pyp.process_list_of_files(["example/k8s/shared.py"], summarize=False)
    print(proc)
