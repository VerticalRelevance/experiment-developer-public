import boto3
import os
import json
from datetime import datetime, timezone
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import ValidationError
from pynamodb.exceptions import DoesNotExist
from params import FunctionGuidelines
from settings import StorageSettings
from pynamodb_models import GenerationOutputModel


class FargateSettings(BaseSettings):
    model_config = SettingsConfigDict()
    cluster_name: str
    task_definition: str
    subnet_id: str
    security_group_id: str
    container_name: str


def create_response(status_code: int, body: dict) -> dict:
    """Helper function to create a standard Lambda response."""
    return {
        "statusCode": status_code,
        "body": json.dumps(body),
        'headers': {
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
        }
    }


def get_query_parameters(event: dict) -> tuple[str, str]:
    """Extracts primary and sort keys from query string parameters."""
    pk = event.get("queryStringParameters", {}).get("pk")
    sk = event.get("queryStringParameters", {}).get("sk")
    return pk, sk


def handle_get_request(pk: str, sk: str) -> dict:
    """Handles GET requests to retrieve generation output."""
    if not pk or not sk:
        return create_response(400, {"error": "Missing 'pk' or 'sk' query parameter"})

    try:
        item = GenerationOutputModel.get(pk, sk)
        return create_response(200, item.attribute_values)
    except DoesNotExist:
        return create_response(
            404, {"error": f"No item found with pk={pk} and sk={sk}"}
        )
    except Exception as e:
        return create_response(500, {"error": str(e)})


def parse_guidelines(data: dict) -> tuple[FunctionGuidelines, list[dict]]:
    """Parses and validates FunctionGuidelines and constructs environment variables."""
    try:
        guidelines = FunctionGuidelines(**data)
    except ValidationError as e:
        error_message = e.errors()
        print(f"Validation error in FunctionGuidelines: {error_message}")
        raise ValidationError(error_message)

    chroma_params = StorageSettings()
    timestamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    environment_variables = [
        {"name": "CHROMA_BUCKET", "value": chroma_params.bucket},
        {"name": "CHROMA_PATH", "value": chroma_params.db_path},
        {"name": "CHOICE", "value": "generate"},
        {"name": "TIMESTAMP", "value": timestamp},
        {"name": "NAME", "value": guidelines.name},
        {"name": "PURPOSE", "value": guidelines.purpose},
        {"name": "SERVICES", "value": json.dumps(guidelines.services)},
    ]
    return guidelines, environment_variables, timestamp


def handle_post_request(data: dict) -> dict:
    """Handles POST requests to initiate a Fargate task with specified environment variables."""
    try:
        guidelines, environment_variables, timestamp = parse_guidelines(data)
    except ValidationError as e:
        return create_response(400, {"error": str(e)})

    status_code, body = run_fargate_task(environment_variables)
    body.update(
        {
            "timestamp": timestamp,
            "name": guidelines.name,
        }
    )
    return create_response(status_code, body)


def run_fargate_task(environment_variables: list[dict]) -> tuple[int, dict]:
    """Runs a Fargate task with the provided environment variables."""
    ecs_client = boto3.client("ecs")
    fargate_settings = FargateSettings()

    try:
        response = ecs_client.run_task(
            cluster=fargate_settings.cluster_name,
            launchType="FARGATE",
            taskDefinition=fargate_settings.task_definition,
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": [fargate_settings.subnet_id],
                    "securityGroups": [fargate_settings.security_group_id],
                    "assignPublicIp": "ENABLED",
                }
            },
            overrides={
                "containerOverrides": [
                    {
                        "name": fargate_settings.container_name,
                        "environment": environment_variables,
                    }
                ]
            },
        )

        task_arn = response["tasks"][0]["taskArn"]
        print(f"Fargate task started with ARN: {task_arn}")
        return 200, {"taskArn": task_arn}

    except Exception as e:
        print(f"Error starting Fargate task: {str(e)}")
        return 502, {"message": str(e)}


def lambda_handler(event, context) -> dict:
    """Main Lambda handler function to route GET and POST requests."""
    print(event)
    try:
        if event["httpMethod"] == "GET":
            pk, sk = get_query_parameters(event)
            print("GET: ", pk, sk)
            return handle_get_request(pk, sk)

        elif event["httpMethod"] == "POST":
            data = json.loads(event["body"])
            print(f"Processing generation for:\n{data}")
            return handle_post_request(data)

        else:
            return create_response(405, {"error": "Method not allowed"})
    except KeyError as e:
        print(f"Missing key in event: {e}")
        return create_response(
            400, {"error": f"Invalid request structure: missing {str(e)}"}
        )
    except Exception as e:
        print(f"Unexpected error: {e}")
        return create_response(500, {"error": str(e)})
