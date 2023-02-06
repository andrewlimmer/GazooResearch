#!/bin/bash

# Relative to start.command file path
cd "$(dirname "$0")"

# OS Query
unameOut="$(uname -s)"
case "${unameOut}" in
    Linux*)     machine=Linux;;
    Darwin*)    machine=Mac;;
    CYGWIN*)    machine=Cygwin;;
    MINGW*)     machine=MinGw;;
    *)          machine="UNKNOWN:${unameOut}"
esac
echo "OS: ${machine}"

# Check if Git Exists
if ! command -v git &> /dev/null
then
  echo "The computer's password is required for GIT Installation:"
  # Install BrewHub
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  echo "Install Git"
  brew install git
fi

# Check OpenSSL Version
if [[ $(openssl version | awk '{print $1}') != "OpenSSL" && $(openssl version | awk '{print $2}') != "1.1.1s" ]]; then
  echo "The computer's password is required for OpenSSL installation:"
  # Install BrewHub
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  # Install OpenSSL
  brew install openssl@1.1
  brew link --force openssl@1.1
  echo 'export PATH="/opt/homebrew/opt/openssl@1.1/bin:$PATH"' >> ~/.zshrc
  source ~/.zshrc
fi

create_ssl () {
  echo "The computer's password is required for HTTPS certificates generation and acceptance:"
  # Generate SSL for nginx
  sudo rm -r ./nginx/certs/*
  # Generate Certificate for https tls ssl
  openssl req -x509 -nodes -days 365 -subj "/C=CA/ST=QC/O=Company, Inc./CN=localhost" -addext "subjectAltName=DNS.1:document.localhost,DNS.2:pgadmin.localhost,DNS.3:jupyter.localhost" -newkey rsa:2048 -keyout ./nginx/certs/nginx-selfsigned.key -out ./nginx/certs/nginx-selfsigned.crt;
  # Remove Certificate if Exists
  sudo security delete-certificate -c "localhost" /Library/Keychains/System.keychain
  # Local computer needs to accept certificate
  sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain ./nginx/certs/nginx-selfsigned.crt
}

create_encryption_key() {
  echo
  echo "Randomly Generated Encryption Keys (256-bit):"
  openssl rand -hex 32
  openssl rand -hex 32
  openssl rand -hex 32
  openssl rand -hex 32
  openssl rand -hex 32
  echo

  # Enter Encryption Key
  while [[ ! (${#encryption_key} == 64 && -z ${encryption_key//[[:digit:][:lower:]]}) ]]
  do
    echo "Enter Encryption Key: (64 characters; lower case letters and numbers allowed)"
    read -s encryption_key
    echo "length:${#encryption_key}"
  done
}

# Pull GitHub
git pull


# Generate SSL Certificate and Key
nginx_key=./nginx/certs/nginx-selfsigned.key
nginx_crt=./nginx/certs/nginx-selfsigned.crt
# Check if files do not exist
if (! [[ -f "$nginx_key" ]]) || (! [[ -f "$nginx_crt" ]] ); then
  create_ssl
fi

# Check if file existed for > 30 days
if [[ $(find "$filename" -mtime +30 -print) ]]; then
  create_ssl
fi

# Create Encryption Key
create_encryption_key

# Write Environment Variables File
rm ./env-variables.txt
echo "POSTGRES_USER=admin" >> ./env-variables.txt
echo "POSTGRES_PASSWORD=$encryption_key" >> ./env-variables.txt
echo "POSTGRES_TDE_PASSWORD=${encryption_key:0:32}" >> ./env-variables.txt
echo "PGADMIN_DEFAULT_EMAIL=admin@admin.com" >> ./env-variables.txt
echo "PGADMIN_DEFAULT_PASSWORD=$encryption_key" >> ./env-variables.txt
echo "PGADMIN_LISTEN_ADDRESS=0.0.0.0" >> ./env-variables.txt

echo 'Start Clinical Document Program'
# Start Docker Compose
docker compose up

# Remove Environment Variables
rm ./env-variables.txt
