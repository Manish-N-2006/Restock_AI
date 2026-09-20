import os
import glob

test_files = glob.glob('tests/test_*.py')
override_code = '''
from app.authorization.principal import get_current_principal
app.dependency_overrides[get_current_principal] = lambda: {
    "uid": {"type": "ReStockAI::User", "id": "manager-test"},
    "attrs": {"role": "MANAGER", "store_scope": "*"},
    "parents": []
}
'''

for file in test_files:
    with open(file, 'r') as f:
        content = f.read()
    
    if 'get_current_principal' not in content:
        # insert after client = TestClient(app)
        parts = content.split('client = TestClient(app)')
        if len(parts) == 2:
            new_content = parts[0] + 'client = TestClient(app)\n' + override_code + parts[1]
            with open(file, 'w') as f:
                f.write(new_content)
            print(f'Updated {file}')
