#!/bin/bash

# Default Values
version=1.25
echo "Version: $version"

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
docker load --input ./docker-images/clinical-document-db-$version-$architecture.tar
# React
docker load --input ./docker-images/clinical-document-react-$version-$architecture.tar
# Flask
docker load --input ./docker-images/clinical-document-flask-$version-$architecture.tar
# Jupyter
docker load --input ./docker-images/clinical-document-jupyter-$version-$architecture.tar
