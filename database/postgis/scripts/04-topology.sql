ALTER TABLE routing_network ADD COLUMN IF NOT EXISTS source INTEGER;
ALTER TABLE routing_network ADD COLUMN IF NOT EXISTS target INTEGER;
SELECT pgr_createTopology('routing_network', 0.001, 'geom', 'osm_id');
