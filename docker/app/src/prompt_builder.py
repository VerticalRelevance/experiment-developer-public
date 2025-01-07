import logging
from typing import Union
import yaml
from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate
from langchain.prompts import PromptTemplate
from src.models.params import GenerationParams
from src.models.dev_plan import SubfunctionGuidelines, StepByStepDevPlan

logger = logging.getLogger(__name__)

class PromptBuilder:
    def __init__(
        self, guideline_parameters: Union[GenerationParams, SubfunctionGuidelines]
    ) -> None:
        self.guideline_parameters = guideline_parameters
        self.function_name = guideline_parameters.name
        self.guidelines = self.__generate_guidelines()
        self.prompts = self._load_prompts()
        logger.info(
            f" Instantiated Prompt Builder with the following guidelines:\n{self.guidelines}"
        )

    @staticmethod
    def _load_prompts():
        """Load prompts from YAML file with caching."""
        prompt_path = Path(__file__).parent / "config" / "prompts.yaml"
        with open(prompt_path, 'r') as f:
            return yaml.safe_load(f)

    @staticmethod
    def dict_to_str_fmt(dict: dict[str, str]):
        return "\n".join([f"{k.capitalize()}: {v}" for k, v in dict.items()])

    def __generate_guidelines(self):
        ignore_list = ["timestamp", "reusable", "function_import_path"]
        gl = self.guideline_parameters.model_dump()
        for key in ignore_list:
            gl.pop(key, None)
        return PromptBuilder.dict_to_str_fmt(gl)

    def get_prompt_template(self, query_var: str = "query"):
        system_template = self.prompts["system"]["developer_role"]
        def substitute(prompt: str):
            return {query_var: prompt}

        template = ChatPromptTemplate.from_messages(
            [("system", system_template), ("user", f"{{{query_var}}}")]
        )
        return template, substitute

    def create_prompt(self, template_key: str, **kwargs) -> str:
        """
        Generic method to create prompts based on template key and parameters.
        
        Args:
            template_key: Dot-separated path to the template in prompts.yaml
            **kwargs: Additional parameters to format the template with
        
        Returns:
            Formatted prompt string
        """
        # Get the template from nested dictionary using the dot notation
        template = self.prompts
        for key in template_key.split('.'):
            template = template[key]
            
        # Always include guidelines in the formatting parameters
        format_params = {'guidelines': self.guidelines}
        format_params.update(kwargs)
        
        return template.format(**format_params)

    def create_dev_plan_prompt(self, map_to_subfunction: bool) -> str:
        template_key = 'development.dev_plan.base'
        prompt = self.create_prompt(template_key)
        
        if map_to_subfunction:
            subfunction_template = self.prompts['development']['dev_plan']['subfunction_mapping']
            prompt += "\n" + subfunction_template
            
        return prompt

    def create_subfunction_dev_plan(self, reusable_candidates: str) -> str:
        return self.create_prompt(
            'development.subfunction_dev_plan',
            reusable_candidates=reusable_candidates
        )

    def create_code_gen_prompt(self, dev_plan: StepByStepDevPlan) -> str:
        steps_str = "\n".join(
            [PromptBuilder.dict_to_str_fmt(step.model_dump())
             for step in dev_plan.list_of_steps]
        )
        return self.create_prompt(
            'development.code_generation',
            steps_str=steps_str
        )

    def create_code_review_prompt(self, code: str) -> str:
        return self.create_prompt(
            'review.code_review',
            code=code
        )

    def create_combine_code_prompt(
        self, generated: list[str], reusable: list[str], combination_notes: str
    ) -> str:
        generated = "\n".join(generated)
        reusable_str = ""
        if reusable:
            reusable_str = (
                "and the following set of reusable functions. Import them as needed\n"
                + "\n\n".join(reusable)
            )
        return self.create_prompt(
            'combination.combine_code',
            generated=generated,
            reusable=reusable_str,
            combination_notes=combination_notes
        )

    def create_resuability_review_prompt(self, candidates: list[str]):
        formated_candidates = "\n".join(candidates)
        return self.prompts["review"]["reusability_review"].format(
            guidelines=self.guidelines,
            candidates=formated_candidates
        )

    @staticmethod
    def get_summarize_prompt():
        prompts = PromptBuilder._load_prompts()
        template = prompts["summarization"]["function_summary"]
        return PromptTemplate(
            template=template,
            input_variables=["lang", "func_json"]
        )
