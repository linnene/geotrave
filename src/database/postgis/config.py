"""PostGIS connection configuration."""

import os

POSTGIS_DSN = os.getenv(
    "POSTGIS_DSN",
    "postgresql://geotrave:geotrave_dev@localhost:5432/geotrave",
)
