source scripts/test_cases/base_exports.sh

export NAME="assert_pod_healthy"
export PURPOSE="assert all the containers in specified Kubernetes pod in a given EKS cluster namespace are healthy and running"
export SERVICES='["eks"]'

python app/main.py $CHOICE