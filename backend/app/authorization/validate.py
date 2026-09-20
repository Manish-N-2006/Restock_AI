import os
import sys
import cedarpy
from .engine import _load_cedar_files

def main():
    try:
        schema, policies = _load_cedar_files()
        
        # Validating policies against schema using cedarpy
        validation_result = cedarpy.validate_policies(policies, schema)
        
        if validation_result.validation_passed:
            print("Cedar policies successfully validated against the schema.")
            sys.exit(0)
        else:
            print("Cedar policy validation failed:")
            for err in validation_result.errors:
                print(f" - {err}")
            sys.exit(1)
    except Exception as e:
        print(f"Error during validation: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
