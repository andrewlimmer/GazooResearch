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

echo "Checking internet connection..."
echo -e "GET http://google.com HTTP/1.0\n\n" | nc google.com 80 -t2 > /dev/null 2>&1
if [ $? -eq 0 ]; then
  echo "Online"

  # Install Homebrew
  which -s brew
  if [[ $? != 0 ]] ; then
    # Install Homebrew
    echo 'Install Homebrew'
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    (echo; echo 'eval "$(/opt/homebrew/bin/brew shellenv)"') >> ~/.bash_profile
    eval "$(/opt/homebrew/bin/brew shellenv)"
  else
    echo 'Update Homebrew'
    brew update
  fi

  # Check if Git Exists
  while ! command -v git &> /dev/null
  do
    echo "The computer's password is required for GIT Installation:"
    brew install git
  done

  # Check OpenSSL Version
  while [[ $(openssl version | awk '{print $1}') != "OpenSSL" && $(openssl version | awk '{print $2}') != "1.1.1s" ]]
  do
    echo "The computer's password is required for OpenSSL installation:"
    # Install OpenSSL
    brew install openssl@1.1
    brew link --force openssl@1.1
    echo 'export PATH="/opt/homebrew/opt/openssl@1.1/bin:$PATH"' >> ~/.zshrc
    source ~/.zshrc
  done

  # Pull GitHub
  git pull

else
  echo "Offline"
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

# Create Encryption Key
create_encryption_key

# Write Environment Variables File
rm ./env-variables.txt
echo "PGADMIN_DEFAULT_EMAIL=admin@admin.com" >> ./env-variables.txt
echo "PGADMIN_DEFAULT_PASSWORD=KQgiUJv1tG16A9hgxIhE32JcxdsANZU7eCi9om3Wlq1RUMnAnZrue" >> ./env-variables.txt
echo "PGADMIN_LISTEN_ADDRESS=0.0.0.0" >> ./env-variables.txt

# Secret
rm ./postgresql-secret.txt
echo "POSTGRES_USER=admin" >> ./postgresql-secret.txt
echo "POSTGRES_PASSWORD=$encryption_key" >> ./postgresql-secret.txt
echo "POSTGRES_TDE_PASSWORD=${encryption_key:0:32}" >> ./postgresql-secret.txt
echo "JUPYTER_TOKEN=$encryption_key" >> ./postgresql-secret.txt

echo 'Start Clinical Document Program'
# Start Docker Compose
docker compose up -d

# Remove Environment Variables
rm ./postgresql-secret.txt