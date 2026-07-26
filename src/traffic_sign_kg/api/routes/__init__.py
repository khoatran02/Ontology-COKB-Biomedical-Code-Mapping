from traffic_sign_kg.api.routes.health import router as health_router
from traffic_sign_kg.api.routes.indexes import router as indexes_router
from traffic_sign_kg.api.routes.search import router as search_router

__all__ = ["health_router", "indexes_router", "search_router"]
