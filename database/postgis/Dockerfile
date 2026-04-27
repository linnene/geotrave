FROM postgis/postgis:17-3.5

RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-17-pgrouting \
    osm2pgsql \
    && rm -rf /var/lib/apt/lists/*

COPY init/ /docker-entrypoint-initdb.d/
COPY scripts/ /scripts/
