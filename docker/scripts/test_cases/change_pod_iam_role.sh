source scripts/test_cases/base_exports.sh

export NAME="change_pod_iam_role"
export PURPOSE="Given a new iam role change the iam role being used by a eks pod to this new role. Additionally, have all active pods stop using the old role and use this new one."
export SERVICES='["eks", "iam"]'

python app/main.py $CHOICE