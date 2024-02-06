#!/bin/bash

echo "stopping Clinical Document"
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
# Go to script directory
cd $SCRIPT_DIR

# Stop Docker
docker compose --file docker-compose.yaml --project-name "gazoo-research" rm --volumes	

# Delete Volumes
docker volume rm gazoo-research_db_data_volume
docker volume rm gazoo-research_db_volume
docker volume rm gazoo-research_pgadmin_volume