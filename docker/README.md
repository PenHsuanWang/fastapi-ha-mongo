# MongoDB ReplicaSet with KeyFile (for Python FastAPI HA)

## 1. Prerequisites

* Linux or macOS with Docker & Docker Compose installed
* Python (3.9+) on your host (for FastAPI)
* `openssl` installed on your host (for generating keyFile)

---

## 2. Generate a MongoDB KeyFile

The keyFile allows MongoDB nodes in a ReplicaSet to authenticate with each other.
Even in single-node dev, this is **mandatory** when you enable authentication.

```bash
openssl rand -base64 756 > mongo-keyfile
chmod 400 mongo-keyfile
```

* File: `mongo-keyfile`
* Must be mode `400` (readable by MongoDB only)

---

## 3. Prepare Docker Compose Configuration

Create `compose.yaml` in your project directory:

```yaml
version: "3.8"
services:
  mongo-ha:
    image: mongo:6
    container_name: mongo-ha
    restart: unless-stopped
    ports:
      - "27017:27017"
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: adminPwd
    command:
      [
        "mongod", "--replSet", "rs0", "--bind_ip_all",
        "--auth", "--keyFile", "/data/keyfile/mongo-keyfile"
      ]
    volumes:
      - ./mongo-keyfile:/data/keyfile/mongo-keyfile:ro
      - ./init:/docker-entrypoint-initdb.d
    healthcheck:
      test: ["CMD-SHELL", "mongosh --quiet --eval 'db.hello().isWritablePrimary' -u admin -p adminPwd"]
      interval: 5s
      retries: 25
```

**Key points:**

* `--replSet rs0`: Enable ReplicaSet
* `--auth`: Enable authentication
* `--keyFile`: Required for auth+replicaSet
* `--bind_ip_all`: Accept external connections
* `./init`: Mounts your initialization scripts (see below)

---

## 4. ReplicaSet Initialization Script

Create a file: `init/00-rs-init.js`

```js
// Replace the IP with your actual host IP!
const cfg = { _id: "rs0", members: [{ _id: 0, host: "192.168.50.10:27017" }] };
try {
  rs.initiate(cfg);
} catch (e) { print(e.message); }
```

* Use your host’s **local LAN IP**, not `localhost` or `mongo-ha`.
* You can find it via `ip addr`, `hostname -I`, or `ifconfig`.

**Why?**
Your Python FastAPI (on host) and MongoDB (in Docker) must agree on the member hostnames/IPs for replica set!

> All drivers (including PyMongo, Motor, Mongo shell) must connect via exactly the same IP/host.

---

## 5. (Optional) HA Schema Script

Create another file: `init/01-ha-schema.js`

```js
db = db.getSiblingDB("sie_ingestor");
/* leader_lock */
db.createCollection("leader_lock", {
  validator: { $jsonSchema: {
    bsonType: "object",
    required: ["_id", "leader_id", "lease_until", "term"],
    properties: {
      _id:         { enum: ["leader_lock"] },
      leader_id:   { bsonType: ["string", "null"] },
      lease_until: { bsonType: "date" },
      term:        { bsonType: "int", minimum: 0 }
} } }});

db.leader_lock.insertOne(
  { _id: "leader_lock", leader_id: null, lease_until: new Date(0), term: 0 },
  { writeConcern: { w: "majority" } }
);

/* runner_state */
db.createCollection("runner_state", {
  validator: { $jsonSchema: {
    bsonType: "object",
    required: ["_id", "last_heartbeat", "term"],
    properties: {
      _id:            { bsonType: "string" },
      last_heartbeat: { bsonType: "date" },
      term:           { bsonType: "int", minimum: 0 }
} } }});
db.runner_state.createIndex({ last_heartbeat: 1 }, { expireAfterSeconds: 30 });

print("[init] HA schema ready");
```

---

## 6. Start MongoDB (ReplicaSet+KeyFile)

```bash
docker compose up -d
```

Wait for a few seconds, until healthcheck passes and MongoDB is ready.

---

## 7. Initialize & Verify ReplicaSet

1. Enter the MongoDB shell:

   ```bash
   docker exec -it mongo-ha mongosh -u admin -p adminPwd
   ```

2. Check replica set status:

   ```js
   rs.status()
   ```

   * If you see `"stateStr": "PRIMARY"`, you are good!

If you see an error about "NotYetInitialized", run the initiate manually:

```js
rs.initiate({
  _id: "rs0",
  members: [{ _id: 0, host: "192.168.50.10:27017" }]
})
```

* Wait a few seconds, and run `rs.status()` again.

---

## 8. Connect from your FastAPI Backend

Set your `.env` for Python like this (use your host IP):

```env
NODE_ID=node1
MONGO_URI=mongodb://admin:adminPwd@192.168.50.10:27017/sie_ingestor?replicaSet=rs0&authSource=admin
PEERS=node2:http://127.0.0.1:8001
LEASE_DURATION=10
ELECTION_INTERVAL=5
HEARTBEAT_INTERVAL=2
```

**Note:**

* The host part (`192.168.50.10`) must match the replica set config and be accessible from your host.

Test connection in Python:

```python
from pymongo import MongoClient
client = MongoClient("mongodb://admin:adminPwd@192.168.50.10:27017/?replicaSet=rs0&authSource=admin")
print(client.admin.command("ping"))
print(client.admin.command("replSetGetStatus"))
```

---

## 9. Troubleshooting

* **keyFile errors**:

  * Ensure `mongo-keyfile` exists, is mounted, and has permission `400`.
  * Both docker-compose and Dockerfile must mount/provide the keyfile.

* **ReplicaSet NotYetInitialized/No Primary**:

  * The member IP/hostname in `rs.initiate` must be reachable and match what Python uses.
  * Don't use `localhost` unless both host and container can resolve it the same way (see notes above).

* **Cannot connect from Python**:

  * Confirm port `27017` is open (`docker ps` and `docker-compose.yaml`).
  * Confirm IP in `.env` is the same as `rs.status()` in MongoDB.

---

## 10. Reference

* [MongoDB: Deploy Replica Set With Keyfile](https://www.mongodb.com/docs/manual/tutorial/deploy-replica-set-with-keyfile-access-control/)
* [PyMongo: Replica Set Connections](https://pymongo.readthedocs.io/en/stable/examples/high_availability.html)

---

# Quick Recap

```bash
# 1. Generate keyfile (only once!)
openssl rand -base64 756 > mongo-keyfile
chmod 400 mongo-keyfile

# 2. Prepare docker compose, init/00-rs-init.js, and (optionally) init/01-ha-schema.js

# 3. Start MongoDB with:
docker compose up -d

# 4. Initialize replica set (if needed)
docker exec -it mongo-ha mongosh -u admin -p adminPwd
> rs.status() # or run rs.initiate() if needed

# 5. Connect from your FastAPI backend using the correct IP/port in your .env
```

---
