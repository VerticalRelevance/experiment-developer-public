from kubernetes import client
from typing import List, Dict, Any
from example.k8s.shared import get_eks_api_client


def retrieve_pod_details(
    api_client: client.ApiClient, namespace: str
) -> List[Dict[str, Any]]:
    v1_api = client.CoreV1Api(api_client)
    pod_list = v1_api.list_namespaced_pod(namespace=namespace)
    pod_details = []
    for pod in pod_list.items:
        pod_info = {
            "name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "status": pod.status.phase,
            "node_name": pod.spec.node_name,
            "host_ip": pod.status.host_ip,
            "pod_ip": pod.status.pod_ip,
            "start_time": pod.status.start_time,
        }
        pod_details.append(pod_info)
    return pod_details


def check_containers_health(pod_details: List[Dict[str, Any]]) -> bool:
    for pod in pod_details:
        containers = pod.get("containers", [])
        for container in containers:
            health_status = container.get("health_status", {}).get("status")
            if health_status != "healthy":
                return False
    return True


def assert_pod_healthy(
    cluster_name: str,
    region: str,
    namespace: str,
    expires: int = 60,
    verify_ssl: bool = False,
) -> bool:
    """
    Assert all the containers in specified Kubernetes pods in a given EKS cluster namespace are healthy and running.

    :param cluster_name: Name of the EKS cluster
    :param region: AWS region where the cluster is hosted
    :param namespace: Kubernetes namespace to check the pods
    :param expires: Token expiration time in seconds (default is 60)
    :param verify_ssl: Whether to verify SSL certificates (default is False)
    :return: True if all containers are healthy, False otherwise
    """
    api_client = get_eks_api_client(cluster_name, region, expires, verify_ssl)
    pod_details = retrieve_pod_details(api_client, namespace)
    return check_containers_health(pod_details)
