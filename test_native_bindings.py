#!/usr/bin/env python3
"""Test native bindings by trying to load the libraries."""

import os
import sys

# Add the package to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_compiler():
    """Test the native compiler bindings."""
    print("\n=== Testing Native Compiler ===")
    try:
        from stoffel.native.compiler import NativeCompiler
        compiler = NativeCompiler(
            library_path="./external/stoffel-lang/target/release/libstoffellang.dylib"
        )
        version = compiler.get_version()
        print(f"✓ Compiler loaded successfully")
        print(f"  Version: {version}")
        return True
    except Exception as e:
        print(f"✗ Failed to load compiler: {e}")
        return False


def test_vm():
    """Test the native VM bindings."""
    print("\n=== Testing Native VM ===")
    try:
        from stoffel.native.vm import NativeVM, is_vm_ffi_available

        # First check if FFI is available
        library_path = "./external/stoffel-vm/target/release/libstoffel_vm.dylib"
        if not is_vm_ffi_available(library_path):
            print("⚠ VM library exists but C FFI not exported")
            print("  The 'cffi' module needs to be exported in stoffel-vm.")
            print("  Add 'pub mod cffi;' to lib.rs and rebuild.")
            return "skip"  # Not a failure, just not available yet

        vm = NativeVM(library_path=library_path)
        print(f"✓ VM loaded successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to load VM: {e}")
        return False


def test_mpc():
    """Test the native MPC bindings."""
    print("\n=== Testing Native MPC ===")
    try:
        from stoffel.native.mpc import NativeShareManager
        manager = NativeShareManager(
            n_parties=4,
            threshold=1,
            robust=True,
            library_path="./external/mpc-protocols/target/release/libstoffelmpc_mpc.dylib"
        )
        print(f"✓ MPC manager loaded successfully")
        print(f"  Parties: {manager.n_parties}, Threshold: {manager.threshold}")
        return True
    except Exception as e:
        print(f"✗ Failed to load MPC manager: {e}")
        return False


def test_core():
    """Test the unified core interface."""
    print("\n=== Testing Core Bindings ===")
    try:
        from stoffel._core import is_native_available, get_binding_method
        print(f"Native available: {is_native_available()}")
        print(f"Binding method: {get_binding_method()}")
        return True
    except Exception as e:
        print(f"✗ Failed to check core: {e}")
        return False


def test_compile_source():
    """Test compiling actual Stoffel source code."""
    print("\n=== Testing Compilation ===")
    try:
        from stoffel.native.compiler import NativeCompiler

        compiler = NativeCompiler(
            library_path="./external/stoffel-lang/target/release/libstoffellang.dylib"
        )

        # Simple Stoffel program (Python-like syntax with 2-space indentation)
        source = """\
main main() -> int64:
  var x = 42
  return x
"""

        bytecode = compiler.compile(source)
        print(f"✓ Compiled successfully")
        print(f"  Bytecode size: {len(bytecode)} bytes")
        print(f"  Magic header: {bytecode[:4]}")
        return True
    except Exception as e:
        print(f"✗ Compilation failed: {e}")
        return False


def test_secret_sharing():
    """Test secret sharing round-trip."""
    print("\n=== Testing Secret Sharing ===")
    try:
        from stoffel.native.mpc import NativeShareManager

        # Create a share manager with 4 parties and threshold 1
        manager = NativeShareManager(
            n_parties=4,
            threshold=1,
            robust=True,
            library_path="./external/mpc-protocols/target/release/libstoffelmpc_mpc.dylib"
        )

        # Secret to share
        secret = 12345

        # Create shares
        shares = manager.create_shares(secret)
        print(f"✓ Created {len(shares)} shares for secret {secret}")

        # Reconstruct from shares
        reconstructed = manager.reconstruct(shares)
        print(f"✓ Reconstructed: {reconstructed}")

        if reconstructed == secret:
            print(f"✓ Secret sharing round-trip successful!")
            return True
        else:
            print(f"✗ Mismatch: expected {secret}, got {reconstructed}")
            return False

    except Exception as e:
        print(f"✗ Secret sharing failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("Testing Native Bindings for Stoffel Python SDK")
    print("=" * 50)

    # Change to the SDK directory
    sdk_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(sdk_dir)
    print(f"Working directory: {os.getcwd()}")

    results = []
    results.append(("Core", test_core()))
    results.append(("Compiler", test_compiler()))
    results.append(("VM", test_vm()))
    results.append(("MPC", test_mpc()))
    results.append(("Compile Source", test_compile_source()))
    results.append(("Secret Sharing", test_secret_sharing()))

    print("\n" + "=" * 50)
    print("Summary:")
    for name, result in results:
        if result == "skip":
            status = "⚠ SKIP (not available)"
        elif result:
            status = "✓ PASS"
        else:
            status = "✗ FAIL"
        print(f"  {name}: {status}")

    # Consider it a success if no tests failed (skips are ok)
    all_passed = all(result in (True, "skip") for _, result in results)
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
