#!/bin/bash

# Default Values
source ./version
echo "Version: $VERSION"

# What Architexture
case $(uname -m) in
    x86_64) architecture=amd64;;
    arm)    architecture=arm;;
    arm64)  architecture=arm64;;
    aarch64) architecture=arm64;;
    *) architecture="UNKNOWN" ;;
esac

# Check Operating System
if [[ $architecture == "arm64" || $architecture == "amd64" ]]; then
  echo "Architecture: $architecture"
else
  echo "Error: Please run on a arm64 or amd64";
  exit 1;
fi

# DB
docker load --input ./docker-images/gazoo-research-db-$VERSION-$architecture.tar
# React
docker load --input ./docker-images/gazoo-research-react-$VERSION-$architecture.tar
# Flask
docker load --input ./docker-images/gazoo-research-flask-$VERSION-$architecture.tar
# Jupyter
docker load --input ./docker-images/gazoo-research-jupyter-$VERSION-$architecture.tar
