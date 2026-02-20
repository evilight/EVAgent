"""Debug test for login endpoint - verbose version"""
import base64

# Encode credentials
credentials = base64.b64encode(b"admin:admin123").decode()
print(f"Encoded credentials: {credentials}")

# Create the Authorization header
auth_header = f"Basic {credentials}"
print(f"Authorization header: {auth_header}")

# Try to decode it back
try:
    decoded = base64.b64decode(credentials).decode("utf-8")
    print(f"Decoded credentials: {decoded}")
    parts = decoded.split(":", 1)
    print(f"Username: {parts[0]}, Password length: {len(parts[1]) if len(parts) > 1 else 0}")
except Exception as e:
    print(f"Error: {e}")
