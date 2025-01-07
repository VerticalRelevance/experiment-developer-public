from kubernetes import client, config
import boto3
from typing import Optional
from example.k8s.shared import get_eks_api_client, patch_eks_deployment


def retrieve_current_iam_role(
    api_client: client.ApiClient, pod_name: str, namespace: str
) -> Optional[str]:
    k8s_client = client.CoreV1Api(api_client)
    try:
        pods = k8s_client.list_namespaced_pod(namespace=namespace)
    except client.exceptions.ApiException as e:
        print(f"Exception when calling CoreV1Api->list_namespaced_pod: {e}")
        return None
    target_pod = None
    for pod in pods.items:
        if pod.metadata.name == pod_name:
            target_pod = pod
            break
    if not target_pod:
        print(f"Pod '{pod_name}' not found in namespace '{namespace}'.")
        return None
    iam_role = target_pod.metadata.annotations.get("eks.amazonaws.com/role-arn")
    if not iam_role:
        print(f"No IAM role associated with pod '{pod_name}'.")
        return None
    return iam_role


def update_pod_iam_role(
    api_client: client.ApiClient, pod_name: str, namespace: str, new_role: str
) -> None:
    v1 = client.CoreV1Api(api_client)
    try:
        pod = v1.read_namespaced_pod(name=pod_name, namespace=namespace)
    except client.exceptions.ApiException as e:
        raise RuntimeError(
            f"Failed to retrieve pod {pod_name} in namespace {namespace}: {e}"
        )
    annotations = pod.metadata.annotations or {}
    current_role = annotations.get("eks.amazonaws.com/role-arn")
    if current_role == new_role:
        print(f"The pod {pod_name} already has the IAM role {new_role}.")
        return
    annotations["eks.amazonaws.com/role-arn"] = new_role
    pod.metadata.annotations = annotations
    try:
        v1.patch_namespaced_pod(name=pod_name, namespace=namespace, body=pod)
    except client.exceptions.ApiException as e:
        raise RuntimeError(
            f"Failed to update pod {pod_name} in namespace {namespace}: {e}"
        )
    try:
        updated_pod = v1.read_namespaced_pod(name=pod_name, namespace=namespace)
        updated_annotations = updated_pod.metadata.annotations
    except client.exceptions.ApiException as e:
        raise RuntimeError(
            f"Failed to verify update for pod {pod_name} in namespace {namespace}: {e}"
        )
    if updated_annotations.get("eks.amazonaws.com/role-arn") != new_role:
        raise AssertionError("IAM role update failed.")
    else:
        print(
            f"Successfully updated IAM role to {new_role} for pod {pod_name} in namespace {namespace}."
        )


def change_pod_iam_role(
    cluster_name: str, region: str, pod_name: str, namespace: str, new_role: str
) -> None:
    api_client = get_eks_api_client(cluster_name=cluster_name, region=region)
    current_role = retrieve_current_iam_role(api_client, pod_name, namespace)
    if not current_role:
        print("Failed to retrieve the current IAM role.")
        return
    update_pod_iam_role(api_client, pod_name, namespace, new_role)
    patch_eks_deployment(
        cluster_name,
        region,
        deployment_name="my-deployment",
        namespace=namespace,
        name=pod_name,
        deployment={
            "metadata": {"annotations": {"eks.amazonaws.com/role-arn": new_role}}
        },
    )
    print(
        f"Successfully changed IAM role from {current_role} to {new_role} across all pods in namespace {namespace}."
    )
