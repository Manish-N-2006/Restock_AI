import cedarpy
from backend.app.authorization.engine import authorize
from backend.app.authorization.entities import build_user_entity, build_generic_entity

prin = build_user_entity("manager-1", "MANAGER", "*")
res = build_generic_entity("Inventory")
result = authorize(prin, "VIEW_INVENTORY", res)
print("Allowed:", result.allowed)
print("Reason:", result.reason)
