CREATE INDEX IF NOT EXISTS idx_poi_geom ON planet_osm_point USING GIST(way);
CREATE INDEX IF NOT EXISTS idx_roads_geom ON planet_osm_roads USING GIST(way);
CREATE INDEX IF NOT EXISTS idx_line_geom ON planet_osm_line USING GIST(way);
CREATE INDEX IF NOT EXISTS idx_polygon_geom ON planet_osm_polygon USING GIST(way);
CREATE INDEX IF NOT EXISTS idx_routing_network_geom ON routing_network USING GIST(geom);
