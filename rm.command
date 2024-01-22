#!/bin/bash

echo "stopping Clinical Document"
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
# Go to script directory
cd $SCRIPT_DIR

# Stop Docker
docker compose --file docker-compose.yaml --project-name "clinical-document" rm --volumes	

# Delete Volumes
docker volume rm clinical-document_db_data_volume
docker volume rm clinical-document_db_volume
docker volume rm clinical-document_pgadmin_volume