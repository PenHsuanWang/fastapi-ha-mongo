const cfg = { _id: "rs0", members: [{ _id: 0, host: "localhost:27017" }] };
try {
  if (rs.status().ok === 0) { rs.initiate(cfg); }
} catch (e) { print(e.message); }