#!/usr/bin/env python3
"""
Quick verification script for Jobbergate TUI.
Tests basic functionality without requiring full authentication.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_imports():
    """Test that all TUI modules can be imported."""
    print("Testing imports...")
    try:
        from jobbergate_cli.tui import JobbergateTUI
        print("  ✓ JobbergateTUI")
        
        from jobbergate_cli.tui.app import JobbergateTUI as TUIApp
        print("  ✓ TUIApp")
        
        from jobbergate_cli.tui.widgets.resource_list import ResourceListWidget
        print("  ✓ ResourceListWidget")
        
        from jobbergate_cli.tui.screens.detail import ResourceDetailScreen
        print("  ✓ ResourceDetailScreen")
        
        return True
    except Exception as e:
        print(f"  ✗ Import failed: {e}")
        return False

def test_structure():
    """Test that the TUI has proper structure."""
    print("\nTesting structure...")
    try:
        from jobbergate_cli.tui.app import JobbergateTUI
        
        # Check required attributes
        assert hasattr(JobbergateTUI, 'CSS'), "Missing CSS attribute"
        print("  ✓ Has CSS styling")
        
        assert hasattr(JobbergateTUI, 'BINDINGS'), "Missing BINDINGS attribute"
        print("  ✓ Has key bindings")
        
        # Check required methods
        assert hasattr(JobbergateTUI, 'compose'), "Missing compose method"
        print("  ✓ Has compose method")
        
        assert hasattr(JobbergateTUI, 'refresh_templates'), "Missing refresh_templates"
        print("  ✓ Has refresh_templates")
        
        assert hasattr(JobbergateTUI, 'refresh_scripts'), "Missing refresh_scripts"
        print("  ✓ Has refresh_scripts")
        
        assert hasattr(JobbergateTUI, 'refresh_submissions'), "Missing refresh_submissions"
        print("  ✓ Has refresh_submissions")
        
        return True
    except Exception as e:
        print(f"  ✗ Structure test failed: {e}")
        return False

def test_cli_integration():
    """Test that TUI is integrated into CLI."""
    print("\nTesting CLI integration...")
    try:
        from typer.testing import CliRunner
        from jobbergate_cli.main import app
        
        # Check that tui command exists by running help
        runner = CliRunner()
        result = runner.invoke(app, ['--help'])
        
        assert 'tui' in result.output.lower(), "TUI command not in help output"
        print("  ✓ TUI command in help")
        
        # Check that tui command has proper description
        assert 'terminal user interface' in result.output.lower(), "TUI description missing"
        print("  ✓ TUI description present")
        
        return True
    except Exception as e:
        print(f"  ✗ CLI integration test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("Jobbergate TUI Verification")
    print("=" * 60)
    
    results = []
    results.append(("Imports", test_imports()))
    results.append(("Structure", test_structure()))
    results.append(("CLI Integration", test_cli_integration()))
    
    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n🎉 All tests passed! TUI is ready to use.")
        print("\nTo launch the TUI:")
        print("  1. Login: jobbergate login")
        print("  2. Launch: jobbergate tui")
        return 0
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
