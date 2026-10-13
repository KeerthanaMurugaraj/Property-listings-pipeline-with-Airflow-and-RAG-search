# Run from the project root, after `conda activate production-rag`:
#     source scripts/env.sh
# It points Airflow at this project instead of ~/airflow.
PROJECT_ROOT="$(pwd)"
if [ ! -d "$PROJECT_ROOT/dags" ]; then
  echo "Run 'source scripts/env.sh' from the project root." >&2
  return 1
fi

export AIRFLOW_HOME="$PROJECT_ROOT/airflow_home"
export AIRFLOW__CORE__DAGS_FOLDER="$PROJECT_ROOT/dags"
export AIRFLOW__CORE__LOAD_EXAMPLES=False
# Local learning setup only: skip the login screen. Never set this on a shared deployment.
export AIRFLOW__CORE__SIMPLE_AUTH_MANAGER_ALL_ADMINS=True
# The address of Agency B's API, as an Airflow connection. The DAG reads it with Connection.get("agency_b").
export AIRFLOW_CONN_AGENCY_B="http://localhost:8081"
# Lets the DAG files import the `listings` and `rag` packages that live next to dags/.
export PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}"
