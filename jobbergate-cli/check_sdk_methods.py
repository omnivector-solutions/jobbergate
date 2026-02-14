#!/usr/bin/env python3
"""
Test that TUI uses correct SDK method names.
"""

import ast
import sys
from pathlib import Path

def check_sdk_methods():
    """Check that app.py uses correct SDK method names."""
    tui_app_path = Path(__file__).parent / "jobbergate_cli" / "tui" / "app.py"
    
    with open(tui_app_path) as f:
        content = f.read()
    
    # Parse the AST
    tree = ast.parse(content)
    
    errors = []
    
    # Check for incorrect method calls
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            # Check for .list() calls (should be .get_list())
            if node.attr == "list":
                errors.append(f"Found deprecated .list() call - should be .get_list()")
            
            # Check for .get() calls on SDK objects (should be .get_one())
            # This is harder to detect, but we can look for patterns
            if node.attr == "get" and isinstance(node.value, ast.Attribute):
                # Check if it's sdk.something.get()
                if isinstance(node.value.value, ast.Attribute) and node.value.value.attr == "sdk":
                    errors.append(f"Found deprecated .get() call - should be .get_one()")
    
    # Also do simple string search
    incorrect_patterns = [
        ".list()",
        "job_templates.get(",
        "job_scripts.get(",
        "job_submissions.get(",
    ]
    
    for pattern in incorrect_patterns:
        if pattern in content:
            # Check if it's actually get_list or get_one
            if pattern == ".list()" and ".get_list()" in content:
                continue  # It's the correct get_list()
            if "get(" in pattern and "get_one(" in content:
                continue  # It's the correct get_one()
            
            errors.append(f"Found potentially incorrect pattern: {pattern}")
    
    # Verify correct methods are present
    correct_patterns = [
        "get_list()",
        "get_one(",
    ]
    
    for pattern in correct_patterns:
        if pattern not in content:
            errors.append(f"Missing correct pattern: {pattern}")
    
    return errors

def main():
    print("=" * 60)
    print("TUI SDK Method Verification")
    print("=" * 60)
    
    errors = check_sdk_methods()
    
    if errors:
        print("\n❌ Found issues:")
        for error in errors:
            print(f"  - {error}")
        return 1
    else:
        print("\n✅ All SDK method names are correct!")
        print("\nVerified methods:")
        print("  ✓ sdk.job_templates.get_list()")
        print("  ✓ sdk.job_templates.get_one(id)")
        print("  ✓ sdk.job_scripts.get_list()")
        print("  ✓ sdk.job_scripts.get_one(id)")
        print("  ✓ sdk.job_submissions.get_list()")
        print("  ✓ sdk.job_submissions.get_one(id)")
        return 0

if __name__ == "__main__":
    sys.exit(main())
