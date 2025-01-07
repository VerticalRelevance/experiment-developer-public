import logging
from typing import Dict, Any
from example.k8s.shared import (
    get_eks_api_client,
    get_eks_deployment,
    patch_eks_deployment,
)


def change_pod_iam_role(
    cluster_name: str,
    region: str,
    namespace: str,
    deployment_name: str,
    new_role_arn: str,
) -> bool:
    """
    Change the IAM role used by pods in an EKS deployment and restart them to apply the change.

    Args:
        cluster_name (str): The name of the EKS cluster.
        region (str): The AWS region of the EKS cluster.
        namespace (str): The Kubernetes namespace of the deployment.
        deployment_name (str): The name of the deployment to update.
        new_role_arn (str): The ARN of the new IAM role to apply.

    Returns:
        bool: True if the operation was successful, False otherwise.
    """
    logging.info(
        f"Changing IAM role for deployment {deployment_name} in cluster {cluster_name}"
    )

    try:
        # Step 1: Get Kubernetes API client
        api_client = get_eks_api_client(cluster_name, region)

        # Step 2: Get current deployment configuration
        current_deployment = get_eks_deployment(
            cluster_name, region, namespace, deployment_name
        )

        # Step 3: Update deployment with new IAM role
        updated_deployment = update_deployment_iam_role(
            current_deployment, new_role_arn
        )

        # Step 4: Apply the updated configuration
        patch_eks_deployment(
            cluster_name, region, deployment_name, namespace, updated_deployment
        )

        # Step 5: Restart pods to apply the new IAM role
        if restart_pods(api_client, namespace, deployment_name):
            logging.info(
                f"Successfully changed IAM role for deployment {deployment_name}"
            )
            return True
        else:
            logging.error(f"Failed to restart pods for deployment {deployment_name}")
            return False

    except Exception as e:
        logging.error(f"Error changing IAM role: {str(e)}")
        return False


def update_deployment_iam_role(
    deployment: Dict[str, Any], new_role_arn: str
) -> Dict[str, Any]:
    """
    Update the deployment configuration with the new IAM role.

    Args:
        deployment (Dict[str, Any]): The original deployment configuration.
        new_role_arn (str): The ARN of the new IAM role.

    Returns:
        Dict[str, Any]: The updated deployment configuration.

    Raises:
        ValueError: If the input parameters are invalid or the IAM role specification is not found.
    """
    logging.info("Updating deployment IAM role")

    if not isinstance(deployment, dict):
        raise ValueError("Deployment must be a dictionary")
    if not isinstance(new_role_arn, str) or not new_role_arn.startswith(
        "arn:aws:iam::"
    ):
        raise ValueError("Invalid IAM role ARN")

    updated_deployment = deployment.copy()

    try:
        updated_deployment["spec"]["template"]["spec"][
            "serviceAccountName"
        ] = new_role_arn
        logging.info(f"IAM role updated to: {new_role_arn}")
    except KeyError:
        logging.error("IAM role specification not found in deployment configuration")
        raise ValueError("IAM role specification not found in deployment configuration")

    logging.info("Deployment configuration successfully updated")
    return updated_deployment


def restart_pods(api_client: Any, namespace: str, deployment_name: str) -> bool:
    """
    Restart all pods in the deployment to apply the new IAM role.

    Args:
        api_client (kubernetes.client.ApiClient): The Kubernetes API client.
        namespace (str): The namespace of the deployment.
        deployment_name (str): The name of the deployment to restart.

    Returns:
        bool: True if the restart was successful, False otherwise.
    """
    try:
        from kubernetes import client
        from kubernetes.client.rest import ApiException
        import time

        # Initialize Kubernetes API client for the Apps V1 API
        apps_v1 = client.AppsV1Api(api_client)

        # Create a patch to trigger a rolling update
        patch = {
            "spec": {
                "template": {
                    "metadata": {
                        "annotations": {
                            "kubectl.kubernetes.io/restartedAt": time.strftime(
                                "%Y-%m-%d-%H:%M:%S"
                            )
                        }
                    }
                }
            }
        }

        # Apply the patch to the deployment
        apps_v1.patch_namespaced_deployment(deployment_name, namespace, patch)

        # Wait for the rollout to complete
        max_wait_time = 300  # 5 minutes
        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            deployment_status = apps_v1.read_namespaced_deployment_status(
                deployment_name, namespace
            )
            if (
                deployment_status.status.updated_replicas
                == deployment_status.status.replicas
                and deployment_status.status.available_replicas
                == deployment_status.status.replicas
            ):
                logging.info(f"Deployment {deployment_name} successfully restarted.")
                return True
            time.sleep(5)

        logging.warning(
            f"Deployment {deployment_name} restart timed out after {max_wait_time} seconds."
        )
        return False

    except ApiException as e:
        logging.error(f"Exception when restarting deployment {deployment_name}: {e}")
        return False
    except Exception as e:
        logging.error(
            f"Unexpected error when restarting deployment {deployment_name}: {e}"
        )
        return False