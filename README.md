# GirderBIDS

A Girder plugin providing support for working with datasets in the Brain Imaging
Data Structure (BIDS) format. The project includes:

- A Girder plugin for managing and handling BIDS datasets within Girder.
- A command-line interface (CLI) for validating and importing BIDS datasets into
  a Girder instance (with or without the plugin).

## 1. Setup

### Ubuntu 22.04:

```bash
pip install ".[cli]"
```

### MacOS

```bash
curl -fsSL https://deno.land/install.sh | sh
deno compile -ERWN -o bids-validator jsr:@bids/validator
pip install ".[cli]"
```

### Windows

BIDS Validation is not supported but you can still use the plugin and the
importer (without validation)

```bash
pip install ".[cli]"
```

## 2. Build girder front

### Ubuntu 22.04

```bash
girder build
```

### MacOS

Install npm using Homebrew :

```bash
brew install node
```

Add the following environment variable:

```bash
export NODE_OPTIONS=--openssl-legacy-provider
```

```bash
girder build
```

## 3. Install mongodb

### Ubuntu 22.04

To set up MongoDB 4.4 on Ubuntu 22.04 execute the following commands :

```bash
curl -fsSL https://pgp.mongodb.com/server-4.4.asc | sudo gpg -o /usr/share/keyrings/mongodb-server-4.4.gpg --dearmor
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-4.4.gpg ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/4.4 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-4.4.list
apt-get update
wget http://archive.ubuntu.com/ubuntu/pool/main/o/openssl/libssl1.1_1.1.1f-1ubuntu2_amd64.deb
sudo dpkg -i libssl1.1_1.1.1f-1ubuntu2_amd64.deb
apt-get install -y mongodb-org mongo-tools
sudo systemctl daemon-reload
systemctl start mongod
systemctl enable mongod
chown mongodb:mongodb /var/log/mongodb/mongod.log
chown -R mongodb:mongodb /var/lib/mongodb/*
```

### MacOS

Add MongoDB 4.4:

```bash
brew tap mongodb/brew
brew install mongodb-community@4.4
brew services start mongodb-community@4.4
```

## 3. Serve girder

```bash
girder serve
```

You can specify a database other than "girder" by creating a girder.cfg with
following content:

```
[database]
uri = "mongodb://localhost:27017/hint"
```

And serve girder with GIRDER_CONFIG env variable:

```
GIRDER_CONFIG=./girder.cfg girder serve
```

## 4. Create admin account with "Register" on localhost:8080

## 5. Login and create API key

## 6. Create assetstore on localhost:8080

## 7. Create a Collection copy the ID of the created collection

## 8. Import BIDS database

```bash
bids-importer --bids_dir ... --api_url http://localhost:8080/api/v1  --api_key ... --location_id ...
```

If you want to ignore the validation step, pass `--ignore_validation` on the
command-line. If you need to upload the dataset directly under a collection or a
user, pass `--location_type {collection / user / folder}` (default is `folder`).
If you want to import the BIDS Dataset using the Girder Plugin, pass
`--use_plugin` on the command-line. If you want to copy BIDS JSON to Girder
metadata, pass `--extract_metadata` on the command-line (works only for
`dataset_description.json` and JSON sidecars).
