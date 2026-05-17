"""PostGIS connection configuration."""

import os

POSTGIS_DSN = os.getenv(
    "POSTGIS_DSN",
    # 默认值仅用于本地开发；生产环境通过环境变量或 .env 注入
    "postgresql://geotrave:geotrave_dev@localhost:5432/geotrave",
)
