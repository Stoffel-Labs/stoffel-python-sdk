"""
MPC-Aware VM Wrapper

Provides a VM wrapper that registers MPC operations as foreign functions,
enabling bytecode execution with real MPC semantics via HoneyBadger engine.

The VM calls back into Python for MPC primitives:
- mpc_multiply: Secure multiplication via HoneyBadger
- mpc_add: Local addition of shares (no network)
- mpc_output: Reconstruct shared value
- mpc_input: Get input share for client
"""

import logging
from typing import Any, Dict, List, Optional

from ..native.vm import NativeVM, is_vm_ffi_available, VMError
from ..native.hb_engine_ffi import (
    HoneyBadgerMpcEngine,
    HBEngineError,
    ShareTypeKind,
    is_hb_engine_available,
)

logger = logging.getLogger(__name__)


class VMWithMPC:
    """
    VM wrapper that integrates MPC operations via foreign function callbacks.

    When the VM executes bytecode that calls registered foreign functions
    (mpc_multiply, mpc_output, etc.), the calls are routed to the
    HoneyBadger MPC engine for real cryptographic operations.

    Example:
        engine = HoneyBadgerMpcEngine(...)
        engine.start_preprocessing()

        mpc_vm = VMWithMPC(engine)
        mpc_vm.setup(bytecode)
        mpc_vm.set_client_inputs(0, [share1, share2])
        result = mpc_vm.execute("main")
    """

    def __init__(self, engine: HoneyBadgerMpcEngine):
        """
        Initialize MPC-aware VM wrapper.

        Args:
            engine: HoneyBadger MPC engine (must have preprocessing complete)
        """
        self._engine = engine
        self._vm: Optional[NativeVM] = None
        self._client_inputs: Dict[int, List[bytes]] = {}  # client_id -> shares
        self._setup_done = False

    def setup(self, bytecode: bytes) -> None:
        """
        Initialize VM with bytecode and register MPC foreign functions.

        Args:
            bytecode: Compiled StoffelVM bytecode

        Raises:
            VMError: If VM initialization fails
            RuntimeError: If VM FFI is not available
        """
        if not is_vm_ffi_available():
            raise RuntimeError(
                "StoffelVM FFI not available. "
                "Build with 'cargo build --release' in external/stoffel-vm"
            )

        self._vm = NativeVM()
        self._vm.load(bytecode)

        # Register MPC operations as foreign functions
        self._vm.register_function("mpc_multiply", self._handle_multiply)
        self._vm.register_function("mpc_add", self._handle_add)
        self._vm.register_function("mpc_output", self._handle_output)
        self._vm.register_function("mpc_input", self._handle_input)
        self._vm.register_function("mpc_sub", self._handle_sub)

        self._setup_done = True
        logger.debug("VMWithMPC setup complete, MPC functions registered")

    def _handle_multiply(self, left_share: Any, right_share: Any) -> bytes:
        """
        Secure multiplication via HoneyBadger engine.

        Called when bytecode executes mpc_multiply(left, right).
        This is the most expensive MPC operation - requires network
        communication to consume Beaver triples.

        Args:
            left_share: Left operand share (bytes)
            right_share: Right operand share (bytes)

        Returns:
            Result share as bytes
        """
        logger.debug("MPC multiply called")

        # Convert to bytes if needed
        left = self._to_bytes(left_share)
        right = self._to_bytes(right_share)

        try:
            result = self._engine.multiply(
                left=left,
                right=right,
                kind=ShareTypeKind.INT,
                width=64,
            )
            logger.debug("MPC multiply completed")
            return result
        except HBEngineError as e:
            logger.error(f"MPC multiply failed: {e}")
            raise

    def _handle_add(self, left_share: Any, right_share: Any) -> bytes:
        """
        Local addition of shares (no network required).

        Addition on secret shares is a local operation that doesn't
        require network communication - each party can add their
        shares independently.

        Args:
            left_share: Left operand share (bytes)
            right_share: Right operand share (bytes)

        Returns:
            Result share as bytes
        """
        logger.debug("MPC add called (local operation)")

        left = self._to_bytes(left_share)
        right = self._to_bytes(right_share)

        # Local addition in the field
        # For now, delegate to engine if available, otherwise do local add
        # TODO: Implement proper field addition
        result = self._add_shares_local(left, right)
        return result

    def _handle_sub(self, left_share: Any, right_share: Any) -> bytes:
        """
        Local subtraction of shares (no network required).

        Like addition, subtraction is a local operation.

        Args:
            left_share: Left operand share (bytes)
            right_share: Right operand share (bytes)

        Returns:
            Result share as bytes
        """
        logger.debug("MPC sub called (local operation)")

        left = self._to_bytes(left_share)
        right = self._to_bytes(right_share)

        result = self._sub_shares_local(left, right)
        return result

    def _handle_output(self, share: Any) -> int:
        """
        Reconstruct shared value via HoneyBadger engine.

        Called when bytecode executes mpc_output(share).
        This reveals the value to all parties (opening).

        Args:
            share: Share to open (bytes)

        Returns:
            Reconstructed integer value
        """
        logger.debug("MPC output called")

        share_bytes = self._to_bytes(share)

        try:
            result = self._engine.open(
                share=share_bytes,
                kind=ShareTypeKind.INT,
                width=64,
            )
            logger.debug(f"MPC output reconstructed: {result}")
            return result
        except HBEngineError as e:
            logger.error(f"MPC output failed: {e}")
            raise

    def _handle_input(self, client_id: Any, input_index: Any) -> bytes:
        """
        Get input share for a client.

        Called when bytecode executes mpc_input(client_id, index).
        Returns the pre-distributed input share for this party.

        Args:
            client_id: Client identifier
            input_index: Index of the input

        Returns:
            Input share as bytes
        """
        cid = int(client_id)
        idx = int(input_index)

        logger.debug(f"MPC input called: client={cid}, index={idx}")

        if cid not in self._client_inputs:
            raise ValueError(f"No inputs found for client {cid}")

        shares = self._client_inputs[cid]
        if idx >= len(shares):
            raise ValueError(
                f"Input index {idx} out of range for client {cid} "
                f"(has {len(shares)} inputs)"
            )

        return shares[idx]

    def set_client_inputs(self, client_id: int, shares: List[bytes]) -> None:
        """
        Store client input shares for execution.

        These shares will be accessible via mpc_input() during execution.
        Also initializes the shares in the HoneyBadger engine.

        Args:
            client_id: Client identifier
            shares: List of input shares for this client
        """
        self._client_inputs[client_id] = shares

        # Also initialize in engine
        if shares:
            combined = b''.join(shares)
            try:
                self._engine.init_client_input(client_id, combined)
                logger.debug(f"Initialized {len(shares)} inputs for client {client_id}")
            except HBEngineError as e:
                logger.warning(f"Failed to init client inputs in engine: {e}")

    def execute(self, function_name: str = "main") -> Any:
        """
        Execute function with MPC semantics.

        All registered MPC operations (multiply, output, etc.) will
        be routed to the HoneyBadger engine during execution.

        Args:
            function_name: Name of function to execute

        Returns:
            Function result

        Raises:
            RuntimeError: If setup() hasn't been called
            VMError: If execution fails
        """
        if not self._setup_done or self._vm is None:
            raise RuntimeError("VM not initialized - call setup() first")

        logger.info(f"Executing function '{function_name}' with MPC semantics")
        result = self._vm.execute(function_name)
        logger.info(f"Execution complete, result: {result}")

        return result

    def execute_with_args(self, function_name: str, args: List[Any]) -> Any:
        """
        Execute function with arguments and MPC semantics.

        Args:
            function_name: Name of function to execute
            args: Arguments to pass to the function

        Returns:
            Function result
        """
        if not self._setup_done or self._vm is None:
            raise RuntimeError("VM not initialized - call setup() first")

        logger.info(f"Executing function '{function_name}' with {len(args)} args")
        result = self._vm.execute_with_args(function_name, args)
        logger.info(f"Execution complete, result: {result}")

        return result

    def _to_bytes(self, value: Any) -> bytes:
        """Convert value to bytes if needed."""
        if isinstance(value, bytes):
            return value
        elif isinstance(value, str):
            return value.encode('utf-8')
        elif isinstance(value, int):
            # Convert int to 8-byte little-endian
            return value.to_bytes(8, byteorder='little', signed=True)
        else:
            raise TypeError(f"Cannot convert {type(value)} to bytes")

    def _add_shares_local(self, left: bytes, right: bytes) -> bytes:
        """
        Local share addition (field arithmetic).

        For simplicity, treat shares as 64-bit integers and add.
        In production, this should use proper field arithmetic.
        """
        # Interpret as little-endian signed integers
        left_int = int.from_bytes(left[:8].ljust(8, b'\x00'), 'little', signed=True)
        right_int = int.from_bytes(right[:8].ljust(8, b'\x00'), 'little', signed=True)

        result_int = left_int + right_int
        return result_int.to_bytes(8, byteorder='little', signed=True)

    def _sub_shares_local(self, left: bytes, right: bytes) -> bytes:
        """
        Local share subtraction (field arithmetic).
        """
        left_int = int.from_bytes(left[:8].ljust(8, b'\x00'), 'little', signed=True)
        right_int = int.from_bytes(right[:8].ljust(8, b'\x00'), 'little', signed=True)

        result_int = left_int - right_int
        return result_int.to_bytes(8, byteorder='little', signed=True)


def is_mpc_vm_available() -> bool:
    """
    Check if MPC-aware VM execution is available.

    Returns:
        True if both VM FFI and HoneyBadger engine FFI are available
    """
    return is_vm_ffi_available() and is_hb_engine_available()
