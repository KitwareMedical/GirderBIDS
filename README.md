# GirderBIDS

A Girder plugin providing support for working with datasets in the Brain Imaging
Data Structure (BIDS) format. The project includes:

- A Girder plugin for managing and handling BIDS datasets within Girder.
- A command-line interface (CLI) for validating and importing BIDS datasets into
  a Girder instance (with or without the plugin).

## 1. Setup the importer CLI

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

### 2. Install MongoDB

If MongoDB is not already installed on your machine, you can install it
following the instructions: https://www.mongodb.com/docs/manual/installation/

#### Ubuntu

https://www.mongodb.com/docs/manual/tutorial/install-mongodb-enterprise-on-ubuntu/#std-label-install-mdb-enterprise-ubuntu
Then:

```bash
sudo systemctl start mongod
```

#### MacOS

https://www.mongodb.com/docs/manual/tutorial/install-mongodb-enterprise-on-os-x/#std-label-install-enterprise-macos
Then:

```bash
brew services start mongodb-community
```

#### Windows

https://www.mongodb.com/docs/manual/tutorial/install-mongodb-enterprise-on-windows/#std-label-install-enterprise-windows

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
