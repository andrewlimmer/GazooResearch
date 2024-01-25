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

# Check Architexture
if [[ $architecture == "amd64" || $architecture == "arm64" ]]; then
  echo "Architexture: $architecture"
else
  echo "Error: Please run on a amd64 or arm chipset computer";
  exit 1;
fi

# DB
docker load --input ./docker-images/clinical-document-db-$VERSION-$architecture.tar
# React
docker load --input ./docker-images/clinical-document-react-$VERSION-$architecture.tar
# Flask
docker load --input ./docker-images/clinical-document-flask-$VERSION-$architecture.tar
# Jupyter
docker load --input ./docker-images/clinical-document-jupyter-$VERSION-$architecture.tar
