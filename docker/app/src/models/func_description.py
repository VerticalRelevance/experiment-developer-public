from pydantic import BaseModel, Field


class FunctionDescription(BaseModel):
    """Fields necessary for describing a function"""

    function_signature: str = Field(
        "Function signature with relevant type hints and defaults if available."
    )
    summary: str = Field("Summary of what the function does and its purpose.")
