import logging
import subprocess
from pathlib import Path
from typing import List, Optional

from src.interfaces.storage_provider import StorageProvider
from src.config.settings import Settings

logger = logging.getLogger(__name__)

class S3StorageProvider(StorageProvider):
    """S3 implementation of the storage provider interface."""
    
    def __init__(self, settings=None):
        self.settings = settings or Settings.get_settings().storage
        
    def download_directory(self, source: str, destination: Path) -> None:
        """Download a directory from S3."""
        logger.info(f"Downloading from s3://{self.settings.bucket}/{source}/ to {destination}")
        self._s3_recursive_copy(
            f"s3://{self.settings.bucket}/{source}/",
            str(destination)
        )
        
    def upload_directory(self, source: Path, destination: str) -> None:
        """Upload a directory to S3."""
        logger.info(f"Uploading from {source} to s3://{self.settings.bucket}/{destination}/")
        self._s3_recursive_copy(
            str(source),
            f"s3://{self.settings.bucket}/{destination}/"
        )
        
    def delete_directory(self, path: str) -> None:
        """Delete a directory from S3."""
        logger.info(f"Deleting directory {path} from bucket {self.settings.bucket}")
        self._run_aws_command([
            "aws", "s3", "rm",
            f"s3://{self.settings.bucket}/{path}",
            "--recursive"
        ])
        
    def delete_files(self, files: List[str]) -> None:
        """Delete specific files from S3."""
        for file in files:
            logger.info(f"Deleting {file} from bucket {self.settings.bucket}")
            self._run_aws_command([
                "aws", "s3", "rm",
                f"s3://{self.settings.bucket}/{file}"
            ])
            
    def list_files(self, directory: str, pattern: Optional[str] = None) -> List[str]:
        """List files in an S3 directory, optionally filtered by pattern."""
        cmd = [
            "aws", "s3", "ls",
            f"s3://{self.settings.bucket}/{directory}/",
            "--recursive"
        ]
        
        if pattern:
            cmd.extend(["--include", pattern])
            
        result = self._run_aws_command(cmd)
        return [
            line.split()[-1] for line in result.stdout.splitlines()
            if line.strip()
        ]
    
    def _s3_recursive_copy(self, source: str, destination: str) -> None:
        """Execute recursive copy command for S3."""
        self._run_aws_command([
            "aws", "s3", "cp",
            source, destination,
            "--recursive"
        ])
        
    def _run_aws_command(self, command: List[str]) -> subprocess.CompletedProcess:
        """Execute AWS CLI command and handle errors."""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True
            )
            if result.stdout:
                logger.debug(result.stdout)
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"AWS command failed: {e.stderr}")
            raise RuntimeError(f"AWS operation failed: {e.stderr}") from e
