FROM mongo:6

ENV MONGO_REPLICA_SET_NAME=rs0 \
    MONGO_INITDB_ROOT_USERNAME=admin \
    MONGO_INITDB_ROOT_PASSWORD=adminPwd

# init JS
COPY init/ /docker-entrypoint-initdb.d/