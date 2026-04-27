-- Add pgRouting topology columns to routing_network
ALTER TABLE routing_network ADD COLUMN IF NOT EXISTS source INTEGER;
ALTER TABLE routing_network ADD COLUMN IF NOT EXISTS target INTEGER;

-- Build topology graph (tolerance 0.001° ≈ 111m at equator)
SELECT pgr_createTopology('routing_network', 0.001, 'geom', 'osm_id');
