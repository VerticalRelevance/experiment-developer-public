TEST_CASE="assert_pod_healthy"

cd docker
source scripts/set_oai_vars.sh
sh scripts/test_cases/$TEST_CASE.sh