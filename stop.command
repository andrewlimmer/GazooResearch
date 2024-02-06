#!/bin/bash

echo "stopping Gazoo Research"
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
# Go to script directory
cd $SCRIPT_DIR

# Stop Docker
docker compose --file docker-compose.yaml --project-name "gazoo-research" down

