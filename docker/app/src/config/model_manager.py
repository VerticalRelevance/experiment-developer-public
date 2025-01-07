import logging
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_aws import ChatBedrockConverse
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from src.config.settings import Settings

logger = logging.getLogger(__name__)

class ModelManager:
    def __init__(self) -> None:
        self.settings = Settings.get_settings().model
        self.chat = self.provision_chat_model()
        self.embeddings = self.provision_embeddings()

    @classmethod
    def get_instance(cls) -> "ModelManager":
        """Get singleton instance of ModelManager."""
        if not hasattr(cls, "_instance"):
            cls._instance = cls()
        return cls._instance

    def provision_chat_model(self) -> BaseChatModel:
        # priority to bedrock
        if self.settings.bedrock_model_id:
            logger.info(f" Using Bedrock model {self.settings.bedrock_model_id} for chat")
            self.chat_provider = "bedrock_anthropic"
            return ChatBedrockConverse(model=self.settings.bedrock_model_id)
        elif self.settings.openai_api_key and self.settings.openai_model_name:
            logger.info(f" Using OpenAI model {self.settings.openai_model_name} for chat")
            model = ChatOpenAI(
                api_key=self.settings.openai_api_key,
                model=self.settings.openai_model_name,
            )
            model = model.bind(
                strict=True
            )  # enforce strict = true for reliable function calling
            self.chat_provider = "openai"
            return model
        else:
            raise ValueError(
                f"No suitable model to provision given model settings"
            )

    def provision_embeddings(self):
        if (
            self.settings.openai_api_key
            and self.settings.openai_embedding_model_name
        ):
            return OpenAIEmbeddings(
                model=self.settings.openai_embedding_model_name,
                api_key=self.settings.openai_api_key,
            )
        else:
            raise ValueError(
                f"No suitable embedding model to provision given model settings"
            )
