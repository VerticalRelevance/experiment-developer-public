import requests
import time

API_URL = ""
TEST_CASE = "assert_pod_healthy"


test_cases = {
    "assert_pod_healthy": {
        "name": "assert_pod_healthy",
        "purpose": "assert all the containers in specified Kubernetes pod in a given EKS cluster namespace is healthy and running",
        "services": ["eks"],
    }
}


if __name__ == "__main__":
    response = requests.post(API_URL, json=test_cases[TEST_CASE])
    response = response.json()
    print("Response:", response)
    print("sleeping 3 minutes to await generation completion")
    time.sleep(180)
    generation = requests.get(
        API_URL, params={"pk": response["name"], "sk": response["timestamp"]}
    )
    print("Generation:\n\n", generation.json()["function_code"])
