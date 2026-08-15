from traffic_sign_kg.api.routes.catalog import router as catalog_router
from traffic_sign_kg.api.routes.health import router as health_router
from traffic_sign_kg.api.routes.ingestions import router as ingestions_router
from traffic_sign_kg.api.routes.problems import router as problems_router

__all__ = ["catalog_router", "health_router", "ingestions_router", "problems_router"]
