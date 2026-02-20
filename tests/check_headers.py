"""Debug what headers requests actually sends"""
import base64
import requests

# Check what requests does with auth
from requests.auth import HTTPBasicAuth

auth = HTTPBasicAuth("admin", "admin123")
print(f"Auth object: {auth}")

# Manually construct what we think it should be
credentials = base64.b64encode(b"admin:admin123").decode()
manual_header = f"Basic {credentials}"
print(f"Manual header: {manual_header}")

# Try with prepared request
req = requests.Request('POST', 'http://localhost:8000/api/v1/auth/login', auth=auth)
prepared = req.prepare()
print(f"Prepared headers: {prepared.headers}")
