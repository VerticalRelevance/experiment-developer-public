import logging
import ast, astor, black, time
from collections import OrderedDict
from langchain_community.callbacks import get_openai_callback
from langchain_community.callbacks.manager import get_bedrock_anthropic_callback
from src.prompt_builder import PromptBuilder
from src.config.settings import Settings
from src.models.params import GenerationParams
from src.models.dev_plan import (
    SubfunctionDevPlan,
    StepByStepDevPlan,
)
from src.models.code_outputs import CodeOutput, CodeReviewOutput, CombinedOutput
from src.config.model_manager import ModelManager
from src.chroma_interface import ExperimentVrClient

logger = logging.getLogger(__name__)


class DeveloperAgent:
    def __init__(self) -> None:
        self.settings = Settings.get_settings()
        self.generation_params = GenerationParams()
        self.models = ModelManager.get_instance()
        self.prompt_builder = PromptBuilder(self.generation_params)
        self.prompt_template, self.substitution = (
            self.prompt_builder.get_prompt_template()
        )
        self.experiment_vr_chroma = ExperimentVrClient()
        self.history = []

    def generate_with_cb(self):
        callback_map = {
            "openai": get_openai_callback,
            "bedrock_anthropic": get_bedrock_anthropic_callback,
        }
        
        callback_function = callback_map.get(self.models.chat_provider)
        
        if callback_function:
            start_time = time.time()
            with callback_function() as cb:
                code = self.generate_function()
                logger.info(cb)
                elapsed_time = time.time() - start_time  # Calculate elapsed time
                logger.info(f"Execution time: {elapsed_time:.2f} seconds")
                return code
        else:
            logger.error(
                f"No suitable callback manager implemented for '{self.models.chat_provider}', defaulting to no callback"
            )
            return self.generate_function()

    def generate_function(self):
        final_plan, reusables = self.reusability_review()
        generated = []

        for subfunction in final_plan.list_of_subfunctions:

            if not subfunction.reusable:
                sub_prompt_builder = PromptBuilder(subfunction)
                logger.info(f" Begin subfuction generation for {subfunction.name}")
                generated.append(self.generate_subfunction(sub_prompt_builder))

        combined_code = self.combine_code(generated, reusables.values())
        total_code = generated + [combined_code.function_code]
        cleaned_code = self.post_process_code(total_code)

        result = combined_code
        result.function_code = cleaned_code

        return result

    def reusability_review(self, prompt_builder: PromptBuilder = None, top_k: int = 5):
        prompt_builder = prompt_builder or self.prompt_builder
        first_plan = self.generate_dev_plan(map_to_subfunctions=False)
        first_plan_str = "\n".join(
            [f"{step.step_number}: {step.purpose}" for step in first_plan.list_of_steps]
        )
        resuability_candidates_search = self.experiment_vr_chroma.similarity_search(
            first_plan_str, k=top_k
        )
        resuability_candidates_formated = [
            f"###\nFunction Signature: {candidate.metadata['function_signature']}\nFunction Summary: {candidate.page_content}\nImport Path: {candidate.metadata['path']}"
            for candidate in resuability_candidates_search
        ]
        resuability_candidates_str = "\n".join(resuability_candidates_formated)

        prompt = prompt_builder.create_subfunction_dev_plan(resuability_candidates_str)

        logger.info(f" Reusability review prompt:\n{prompt}")

        reusability_model = self.models.chat.with_structured_output(SubfunctionDevPlan)
        chain = self.prompt_template | reusability_model
        response = chain.invoke(self.substitution(prompt))
        self.history.append((prompt, response))

        self.main_plan = response

        reusables = {
            subfunction.function_import_path.split(".")[-1]: "place_holder"
            for subfunction in response.list_of_subfunctions
            if subfunction.reusable
        }

        for doc, candidate in zip(
            resuability_candidates_search, resuability_candidates_formated
        ):
            function_name = doc.metadata["path"].split(".")[-1]
            if function_name in reusables:
                reusables[function_name] = candidate

        logger.info(f"Reusability Reviewed Dev Plan\n{response}")
        logger.info(f"Reusables:\n{reusables}")
        return response, reusables

    def generate_dev_plan(
        self, map_to_subfunctions: bool, prompt_builder: PromptBuilder = None
    ):
        schema = SubfunctionDevPlan if map_to_subfunctions else StepByStepDevPlan

        prompt_builder = prompt_builder or self.prompt_builder
        prompt_template, substitution = prompt_builder.get_prompt_template()

        dev_plan_model = self.models.chat.with_structured_output(schema)
        chain = prompt_template | dev_plan_model

        prompt = prompt_builder.create_dev_plan_prompt(map_to_subfunctions)
        logger.info(f"\nGenerate dev plan with following prompt:\n{prompt}")

        response = chain.invoke(substitution(prompt))
        logger.info(f"\n Response:\n{response}")
        self.history.append((prompt, response))

        return response

    def generate_subfunction(self, prompt_builder: PromptBuilder):

        sub_prompt_template, substitution = prompt_builder.get_prompt_template()
        dev_plan = self.generate_dev_plan(
            map_to_subfunctions=False, prompt_builder=prompt_builder
        )

        code_gen_prompt = prompt_builder.create_code_gen_prompt(dev_plan)
        code_gen_model = self.models.chat.with_structured_output(CodeOutput)
        code_gen_chain = sub_prompt_template | code_gen_model

        logger.info(f"\nGenerating code with following prompt:\n{code_gen_prompt}")

        code = code_gen_chain.invoke(substitution(code_gen_prompt))
        self.history.append((code_gen_prompt, code))

        logger.info(f"\n Code generated:\n{code.function_code}\n")

        code_review_prompt = prompt_builder.create_code_review_prompt(
            code.function_code
        )
        code_review_model = self.models.chat.with_structured_output(CodeReviewOutput)
        code_review_chain = sub_prompt_template | code_review_model

        logger.info(
            f"\n Starting code review with following prompt:\n{code_gen_prompt}"
        )

        result = code_review_chain.invoke(substitution(code_review_prompt))
        self.history.append((code_review_prompt, result))
        logger.info(f" Needs revision? {result.needs_revision}\n{result.revised_code}")

        return result.revised_code if result.needs_revision else code.function_code

    def combine_code(self, generated: list[str], reusables: list[str]):
        prompt = self.prompt_builder.create_combine_code_prompt(
            generated, reusables, self.main_plan.combination_notes
        )
        combine_code_model = self.models.chat.with_structured_output(CombinedOutput)
        chain = self.prompt_template | combine_code_model

        logger.info(f"\n Combine code with following prompt:\n{prompt}")

        response = chain.invoke(self.substitution(prompt))
        self.history.append((prompt, response))

        logger.info(f"\n Combined Code:\n{response.function_code}")
        logger.info(f"\n Commentary:\n{response.commentary}")
        logger.info(f"\n Sample Usage Python:\n{response.sample_usage_python}")
        logger.info(f"\n Sample Usage CTK:\n{response.sample_usage_chaos_toolkit}")

        return response

    def post_process_code(self, code_sequence: list[str]) -> str:
        try:
            merged_imports = OrderedDict()
            combined_functions = OrderedDict()
            combined_code = []

            for code in code_sequence:
                tree = ast.parse(code)

                for node in tree.body:
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if alias.name not in merged_imports:
                                merged_imports[alias.name] = alias.asname
                    elif isinstance(node, ast.ImportFrom):
                        if node.module not in merged_imports:
                            merged_imports[node.module] = {}
                        for alias in node.names:
                            merged_imports[node.module][alias.name] = alias.asname
                    elif isinstance(node, ast.FunctionDef):
                        func_name = node.name
                        combined_functions[func_name] = node
                    else:
                        combined_code.append(node)

            final_imports = []
            for module, imports in merged_imports.items():
                if isinstance(imports, dict):
                    names = [
                        ast.alias(name=name, asname=asname)
                        for name, asname in imports.items()
                    ]
                    final_imports.append(
                        ast.ImportFrom(module=module, names=names, level=0)
                    )
                else:
                    final_imports.append(
                        ast.Import(names=[ast.alias(name=module, asname=imports)])
                    )

            final_body = (
                final_imports + list(combined_functions.values()) + combined_code
            )
            final_tree = ast.Module(body=final_body)

            final_code = astor.to_source(final_tree)

        except Exception as e:
            logger.error(f"An error occurred during AST processing: {e}")
            logger.info("Falling back to simple string concatenation.")
            final_code = "\n\n".join(code_sequence)

        final_code = black.format_str(final_code, mode=black.FileMode())
        logger.info(f"\n Finalized Code:\n{final_code}")
        return final_code
