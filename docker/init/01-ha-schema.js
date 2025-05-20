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