#!/usr/bin/env python3
"""
Diagnostic script to check Notion client installation and available methods.
Run this to troubleshoot database query issues.
"""

import sys

print("="*60)
print("Notion Client Diagnostic Tool")
print("="*60)

# Check if notion_client is installed
print("\n1. Checking for notion_client library...")
try:
    from notion_client import Client
    print("   ✓ notion_client is installed")
except ImportError as e:
    print(f"   ✗ notion_client is NOT installed: {e}")
    print("\n   SOLUTION: Run: pip install notion-client")
    sys.exit(1)

# Check version
print("\n2. Checking notion_client version...")
try:
    import notion_client
    version = getattr(notion_client, '__version__', 'unknown')
    print(f"   Version: {version}")
    if version == 'unknown':
        print("   ⚠ Warning: Could not determine version")
except Exception as e:
    print(f"   ⚠ Error checking version: {e}")

# Create a test client
print("\n3. Creating test client...")
try:
    client = Client(auth="test_token_for_diagnostic")
    print("   ✓ Client created successfully")
except Exception as e:
    print(f"   ✗ Error creating client: {e}")
    sys.exit(1)

# Check databases endpoint
print("\n4. Checking databases endpoint...")
try:
    databases_endpoint = client.databases
    print(f"   ✓ databases endpoint exists")
    print(f"   Type: {type(databases_endpoint)}")
except Exception as e:
    print(f"   ✗ Error accessing databases endpoint: {e}")
    sys.exit(1)

# Check available methods
print("\n5. Available methods on databases endpoint:")
methods = [m for m in dir(databases_endpoint) if not m.startswith('_')]
if methods:
    for method in methods:
        print(f"   - {method}")
else:
    print("   ⚠ No public methods found")

# Check specifically for query method
print("\n6. Checking for 'query' method...")
if hasattr(databases_endpoint, 'query'):
    print("   ✓ databases.query() method EXISTS")
    print(f"   Method type: {type(getattr(databases_endpoint, 'query'))}")
else:
    print("   ✗ databases.query() method DOES NOT EXIST")
    print("\n   PROBLEM IDENTIFIED!")
    print("   You may have the wrong library installed.")
    print("\n   SOLUTION:")
    print("   1. Uninstall incorrect libraries:")
    print("      pip uninstall notion-py notion")
    print("   2. Install the correct library:")
    print("      pip install notion-client")
    print("   3. Re-run this diagnostic script")

# Check for other Notion libraries
print("\n7. Checking for conflicting Notion libraries...")
conflicting_libs = []
try:
    import notion
    conflicting_libs.append('notion')
except ImportError:
    pass

if conflicting_libs:
    print(f"   ⚠ WARNING: Found conflicting libraries: {', '.join(conflicting_libs)}")
    print("   These may interfere with notion-client")
    print("   Consider uninstalling: pip uninstall " + " ".join(conflicting_libs))
else:
    print("   ✓ No conflicting libraries found")

print("\n" + "="*60)
print("Diagnostic Complete")
print("="*60)

# Summary
if hasattr(databases_endpoint, 'query'):
    print("\n✓ Your Notion client installation looks correct!")
    print("  You should be able to use chat_parser.py")
else:
    print("\n✗ Your Notion client installation has issues!")
    print("  Please follow the solutions above and re-run this script")
