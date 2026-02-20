"""Test if standalone_api module imports correctly"""
try:
    import standalone_api
    print("Import successful")
    print(f"LoginRequest exists: {hasattr(standalone_api, 'LoginRequest')}")
    print(f"LoginResponse exists: {hasattr(standalone_api, 'LoginResponse')}")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
