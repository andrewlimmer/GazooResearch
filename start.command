#!/bin/bash

# Relative to start.command file path
cd "$(dirname "$0")"

# What OS
unameOut="$(uname -s)"
case "${unameOut}" in
    Linux*)     machine=Linux;;
    Darwin*)    machine=Mac;;
    CYGWIN*)    machine=Cygwin;;
    MINGW*)     machine=MinGw;;
    *)          machine="UNKNOWN:${unameOut}"
esac


# Check Operating System
if [[ $machine == "Mac" || $machine == "Linux" ]]; then
  echo "Machine: $machine"
else
  echo "Error: Please run on a Apple Computer or Linux";
  exit 1;
fi

# Check if OpenSSL Exists
if [[ $(openssl version | awk '{print $1}') != "OpenSSL" ]]; then
  echo "Error: OpenSSL is required. Installation information found in ReadMe or Wiki"
  exit 127
fi

# Check if Git Exists
if ! command -v git &> /dev/null; then
  echo "Error: GIT is required. Installation information found in ReadMe or Wiki"
fi

create_ssl () {
  echo "The computer's password is required for HTTPS certificates generation and acceptance:"

  # Generate SSL for nginx
  sudo rm -r ./nginx/certs/*

  # Generate Directory
  mkdir ./nginx/certs
  # Generate Certificate for https tls ssl
  openssl req -x509 -nodes -days 365 -subj "/C=CA/ST=QC/O=Company, Inc./CN=localhost" -addext "subjectAltName=DNS.1:document.localhost,DNS.2:pgadmin.localhost,DNS.3:jupyter.localhost" -newkey rsa:2048 -keyout ./nginx/certs/nginx-selfsigned.key -out ./nginx/certs/nginx-selfsigned.crt;
  # Remove Certificate if Exists
  sudo security delete-certificate -c "localhost" /Library/Keychains/System.keychain
  # Local computer needs to accept certificate
  sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain ./nginx/certs/nginx-selfsigned.crt
}

create_encryption_key() {
  echo
  echo "Randomly Generated (256-bit) Encryption Keys:"
  openssl rand -hex 32
  openssl rand -hex 32
  openssl rand -hex 32
  openssl rand -hex 32
  openssl rand -hex 32
  openssl rand -hex 32
  echo

  # Enter Encryption Key
  while [[ ! $encryption_key =~ ^[a-f0-9]{64}$ ]]
  do
    echo "Enter Encryption Key: (64 Hexadecimal; lower case letters [a-f] and numbers allowed):"
    read -s encryption_key
    echo "length:${#encryption_key}"
  done
}


# Generate SSL Certificate and Key
nginx_key=./nginx/certs/nginx-selfsigned.key
nginx_crt=./nginx/certs/nginx-selfsigned.crt

# Check if files do not exist
while (! [[ -f "$nginx_key" ]]) || (! [[ -f "$nginx_crt" ]] )
do
  create_ssl
done

# Check if file existed for > 30 days
echo "Are certificates >30 days old?"
while [[ $(find "$filename" -mtime +30 -print) ]]
do
  create_ssl
done

# Create Basic HTTP Authentication Username and Password
#echo "Create htpasswd"
#read -p "Username: " USERNAME
#read -s -p "Password: " PASSWORD; echo
#printf "${USERNAME}:$(openssl passwd -crypt ${PASSWORD})\n" >> ./nginx/conf/.htpasswd

# Create Encryption Key
create_encryption_key

# Write Environment Variables File
rm ./env-variables.txt
echo "PGADMIN_DEFAULT_EMAIL=admin@admin.com" >> ./env-variables.txt
echo "PGADMIN_DEFAULT_PASSWORD=KQgiUJv1tG16A9hgxIhE32JcxdsANZU7eCi9om3Wlq1RUMnAnZrue" >> ./env-variables.txt
echo "PGADMIN_LISTEN_ADDRESS=0.0.0.0" >> ./env-variables.txt
echo "JUPYTER_TOKEN=KQgiUJv1tG16A9hgxIhE32JcxdsANZU7eCi9om3Wlq1RUMnAnZrue" >> ./env-variables.txt

# Secret
rm ./postgresql/secrets/postgresql-secret.txt
echo "POSTGRES_USER=admin" >> ./postgresql/secrets/postgresql-secret.txt
echo "POSTGRES_PASSWORD=$encryption_key" >> ./postgresql/secrets/postgresql-secret.txt
echo "POSTGRES_TDE_PASSWORD=${encryption_key:0:32}" >> ./postgresql/secrets/postgresql-secret.txt

echo 'Start Clinical Document'
# Start Docker Compose
if [[ $machine == "Linux" ]]; then
  echo "Machine: $machine";
  UID=${UID} GID=${GID} docker compose up -d;
elif [[ $machine == "Mac" ]]; then
  UID='' GID='' docker compose up -d;
fi