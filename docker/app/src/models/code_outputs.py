from pydantic import BaseModel, Field
from typing import Optional

class CodeOutput(BaseModel):
    """Structure for code generation outputs"""

    function_code: str = Field(description="Full function code as a string")


class CombinedOutput(CodeOutput):
    """Structure for complete, combined code"""

    commentary: str = Field(description="Any notes or commentary on the code")
    sample_usage_python: str = Field(
        description="example execution through a python code snippet"
    )
    sample_usage_chaos_toolkit: str = Field(
        description="example execution as an action/probe through the chaos toolkit framework, in the method section. Return Yaml snippet"
    )


class CodeReviewOutput(BaseModel):
    """Structure for code review outputs"""

    needs_revision: bool = Field(
        description="True if the function needs revision, else False"
    )
    revised_code: Optional[str] = Field(
        description="Revised code, if code needs revision. Populate only if needs_revision is True."
    )
