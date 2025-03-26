# GirderBIDS

Girder plugin to import a BIDS database

## 1. Setup

```bash
pip install girder girder-client fire bids-validator-deno
```

## 2. Build girder front
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

## 3. Serve girder

```bash
girder serve
```

You can specify a database other than "girder" by creating a girder.cfg with following content:

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
## 7. Create a Collection and a Folder in the collection, copy the ID of the created Folder

## 8. Import BIDS database

```bash
python tools/bids-importer.py  --bids_dir ... --girder_api_url http://localhost:8080/api/v1  --girder_api_key ... --girder_folder_id ...
```

If you want to ignore the validation step, pass `--ignore_validation` on the command-line.
