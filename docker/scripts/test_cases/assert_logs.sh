# source the correct model vars
source scripts/test_cases/base_exports.sh

export NAME="assert_logs_contain"
export PURPOSE="given a lambda name and a search string, get the cloudwatch log group associated with that lambda and search the most recent logs to see if any of them contain the passed in search string"
export SERVICES='["logs"]'

python app/main.py 