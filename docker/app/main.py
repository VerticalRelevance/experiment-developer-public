import logging, os, argparse, boto3, subprocess
from src.developer_agent import DeveloperAgent
from src.ingestion_agent import IngestionAgent
from src.models.pynamodb_models import GenerationOutputModel
from src.models.code_outputs import CombinedOutput
from pynamodb.exceptions import PutError


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def write_generation_output(name: str, timestamp: str, combined_output: CombinedOutput):
    try:
        output = GenerationOutputModel(
            pk=name,
            sk=timestamp,
            function_code=combined_output.function_code,
            commentary=combined_output.commentary,
            sample_usage_python=combined_output.sample_usage_python,
            sample_usage_chaos_toolkit=combined_output.sample_usage_chaos_toolkit,
        )

        output.save()
        print("Data saved successfully!")
    except PutError as e:
        print(f"Error saving data: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("choice", choices=["ingest", "generate"])
    parser.add_argument("-s", "--summary", action="store_true")
    args = parser.parse_args()
    ia = IngestionAgent()

    if args.choice == "ingest":
        logger.info("Begining Ingestion Agent...")
        result = ia.ingest()

    elif args.choice == "generate":
        ia.get_current_chroma_db()
        logger.info("Begin AP Developer")
        da = DeveloperAgent()
        result = da.generate_with_cb()
        write_generation_output(
            da.generation_params.name, da.generation_params.timestamp, result
        )
