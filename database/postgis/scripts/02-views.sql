-- POI unified search view for Agent queries
CREATE OR REPLACE VIEW geotrave_poi AS
SELECT
    osm_id,
    name,
    amenity       AS category,
    tourism       AS sub_category,
    ST_Transform(way, 4326) AS geom,
    ST_X(ST_Transform(way, 4326)) AS lng,
    ST_Y(ST_Transform(way, 4326)) AS lat
FROM planet_osm_point
WHERE amenity IS NOT NULL OR tourism IS NOT NULL;

-- Routing network table for pgRouting
DROP TABLE IF EXISTS routing_network CASCADE;
CREATE TABLE routing_network AS
SELECT
    osm_id,
    name,
    highway,
    oneway,
    ST_Length(ST_Transform(way, 4326)::geography) AS length_m,
    ST_Transform(way, 4326) AS geom
FROM planet_osm_roads
WHERE highway IS NOT NULL;
