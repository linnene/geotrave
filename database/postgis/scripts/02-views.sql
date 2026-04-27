-- POI unified search view for Agent queries
CREATE OR REPLACE VIEW geotrave_poi AS
SELECT
    osm_id,
    name,
    amenity       AS category,
    tourism       AS sub_category,
    way           AS geom,
    ST_X(way)     AS lng,
    ST_Y(way)     AS lat,
    tags          AS raw_tags
FROM planet_osm_point
WHERE amenity IS NOT NULL OR tourism IS NOT NULL;

-- Routing network table for pgRouting (must be a TABLE for pgr_createTopology)
DROP TABLE IF EXISTS routing_network CASCADE;
CREATE TABLE routing_network AS
SELECT
    osm_id,
    name,
    highway,
    maxspeed,
    oneway,
    ST_Length(way::geography) AS length_m,
    way AS geom
FROM planet_osm_roads
WHERE highway IS NOT NULL;
