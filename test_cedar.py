import cedarpy
from backend.app.authorization.engine import _load_cedar_files
schema, policies = _load_cedar_files()
res = cedarpy.validate_policies(policies, schema)
if not res.validation_passed:
    for e in res.errors: print(e)
