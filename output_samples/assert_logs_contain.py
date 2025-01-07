import boto3
from botocore.exceptions import ClientError


def get_log_group_name(lambda_name: str) -> str:
    try:
        logs_client = boto3.client("logs")
        paginator = logs_client.get_paginator("describe_log_groups")
        for page in paginator.paginate():
            for log_group in page.get("logGroups", []):
                log_group_name = log_group.get("logGroupName", "")
                if log_group_name == f"/aws/lambda/{lambda_name}":
                    return log_group_name
        raise ValueError(f"Log group for Lambda function {lambda_name} not found.")
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        raise RuntimeError(
            f"An error occurred ({error_code}): {e.response['Error']['Message']}"
        )


def fetch_recent_logs(log_group_name: str) -> list:
    client = boto3.client("logs")
    if not isinstance(log_group_name, str) or not log_group_name.strip():
        raise ValueError("log_group_name must be a non-empty string")
    try:
        response = client.describe_log_groups(logGroupNamePrefix=log_group_name)
        if not any(
            group["logGroupName"] == log_group_name for group in response["logGroups"]
        ):
            raise ValueError("Specified log group does not exist")
        log_streams = client.describe_log_streams(
            logGroupName=log_group_name,
            orderBy="LastEventTime",
            descending=True,
            limit=1,
        )
        if not log_streams["logStreams"]:
            return []
        most_recent_log_stream = log_streams["logStreams"][0]["logStreamName"]
        log_events = client.get_log_events(
            logGroupName=log_group_name,
            logStreamName=most_recent_log_stream,
            startFromHead=False,
        )
        parsed_events = [event["message"] for event in log_events["events"]]
        return parsed_events
    except ClientError as e:
        print(f"An error occurred: {e}")
        return []


def search_logs_for_string(logs: list, search_string: str) -> bool:
    """
    Searches through a list of log entries to determine if any contain the specified search string.

    Parameters:
    logs (list): A list of log entries, each entry being a string.
    search_string (str): The string to search for in the log entries.

    Returns:
    bool: True if the search_string is found in any log entry, False otherwise.
    """
    if search_string == "":
        return False
    for log in logs:
        if search_string in log:
            return True
    return False


def assert_logs_contain(lambda_name: str, search_string: str) -> bool:
    """
    Given a Lambda function's name and a search string, this function checks whether the most recent logs
    of the Lambda function contain the search string.

    Parameters:
    lambda_name (str): The name of the Lambda function.
    search_string (str): The string to search for in the log entries.

    Returns:
    bool: True if the search string is found in the most recent log entries, False otherwise.
    """
    try:
        logs_client = boto3.client("logs")
        paginator = logs_client.get_paginator("describe_log_groups")
        for page in paginator.paginate():
            for log_group in page.get("logGroups", []):
                log_group_name = log_group.get("logGroupName", "")
                if log_group_name == f"/aws/lambda/{lambda_name}":
                    log_streams = logs_client.describe_log_streams(
                        logGroupName=log_group_name,
                        orderBy="LastEventTime",
                        descending=True,
                        limit=1,
                    )
                    if not log_streams["logStreams"]:
                        return False
                    most_recent_log_stream = log_streams["logStreams"][0][
                        "logStreamName"
                    ]
                    log_events = logs_client.get_log_events(
                        logGroupName=log_group_name,
                        logStreamName=most_recent_log_stream,
                        startFromHead=False,
                    )
                    for event in log_events["events"]:
                        if search_string in event["message"]:
                            return True
                    return False
        raise ValueError(f"Log group for Lambda function {lambda_name} not found.")
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        raise RuntimeError(
            f"An error occurred ({error_code}): {e.response['Error']['Message']}"
        )


if __name__ == "__main__":

    lambda_name = "test"
    search_string = "test"

    result = assert_logs_contain(lambda_name, search_string)
    print(f"Search string found in logs: {result}")
