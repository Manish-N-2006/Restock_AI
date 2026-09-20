import cedarpy
import inspect
print(dir(cedarpy))
if hasattr(cedarpy, 'is_authorized'):
    print(inspect.signature(cedarpy.is_authorized))
