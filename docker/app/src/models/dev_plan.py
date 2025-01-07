from pydantic import BaseModel, Field
from typing import Optional
from src.models.params import FunctionGuidelines


class SubfunctionGuidelines(FunctionGuidelines):
    """Fields neccessary for defining a subfunction"""

    function_signature: str = Field(
        description="The function signature with type annotations"
    )

    reusable: bool = Field(
        description="Whether this function is an already available reusable function"
    )

    function_import_path: Optional[str] = Field(
        "Import path of function that is resuable. Include only if reusable: true"
    )


class SubfunctionDevPlan(BaseModel):
    """Development plan mapping steps to subfunctions"""

    list_of_subfunctions: list[SubfunctionGuidelines] = Field(
        description="List of subfunctions that will compose each step of the dev plan"
    )
    main_function: SubfunctionGuidelines = Field(
        description="Final combined function details"
    )
    combination_notes: str = Field(
        description="Explanation of how the subfunctions should be combined"
    )


class Step(BaseModel):
    """Individual step in step by step plan"""

    step_number: int = Field(description="The step number in the step by step sequence")
    purpose: str = Field(description="What this step should accomplish")
    # boto3_services: list[str] = Field(
    #     description="List of Boto3 resources we expect to use"
    # )


class StepByStepDevPlan(BaseModel):
    """High level plan for implementing a function step by step"""

    list_of_steps: list[Step] = Field(
        description="List of steps composing the dev plan"
    )
