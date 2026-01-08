"""
HoneyBadger MPC Client FFI bindings

Raw ctypes bindings for HoneyBadger MPC client operations.
Based on: mpc-protocols/mpc/src/ffi/honey_badger_bindings.h
"""

import ctypes
from ctypes import POINTER, c_int, c_size_t, c_uint64
from typing import Optional, List

from ._lib_loader import get_mpc_library, LibraryLoadError
from .types import (
    U256,
    U256Slice,
    ByteSlice,
    HoneyBadgerMPCClientOpaque,
    NetworkOpaque,
    FieldKind,
)
from .errors import (
    HoneyBadgerErrorCode,
    HoneyBadgerError,
    check_hb_error,
)


class HoneyBadgerClientFFI:
    """
    Raw HoneyBadger MPC Client FFI bindings

    Provides direct access to the C FFI functions for HoneyBadger
    MPC client operations. Functions are lazily initialized on first use.
    """

    _instance: Optional["HoneyBadgerClientFFI"] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        try:
            self._lib = get_mpc_library()
            self._setup_functions()
            self._initialized = True
        except LibraryLoadError:
            self._lib = None
            self._initialized = True

    @property
    def available(self) -> bool:
        """Check if HoneyBadger FFI is available"""
        return self._lib is not None

    def _setup_functions(self):
        """Set up C function signatures"""
        lib = self._lib

        # new_honey_badger_mpc_client
        lib.new_honey_badger_mpc_client.argtypes = [
            c_size_t,           # id
            c_size_t,           # n (number of parties)
            c_size_t,           # t (threshold)
            c_uint64,           # instance_id
            U256Slice,          # inputs
            c_size_t,           # input_len
            c_int,              # field_kind
        ]
        lib.new_honey_badger_mpc_client.restype = POINTER(HoneyBadgerMPCClientOpaque)

        # hb_client_process - Process incoming message
        lib.hb_client_process.argtypes = [
            POINTER(HoneyBadgerMPCClientOpaque),  # client_ptr
            POINTER(NetworkOpaque),               # net_ptr
            ByteSlice,                            # raw_msg
        ]
        lib.hb_client_process.restype = c_int  # HoneyBadgerErrorCode

        # hb_client_get_output - Get computation output
        lib.hb_client_get_output.argtypes = [
            POINTER(HoneyBadgerMPCClientOpaque),  # client_ptr
            POINTER(U256),                        # returned_output
            c_int,                                # field_kind
        ]
        lib.hb_client_get_output.restype = c_int  # HoneyBadgerErrorCode

        # free_honey_badger_mpc_client
        lib.free_honey_badger_mpc_client.argtypes = [
            POINTER(HoneyBadgerMPCClientOpaque),
        ]
        lib.free_honey_badger_mpc_client.restype = None

        # free_network
        lib.free_network.argtypes = [POINTER(NetworkOpaque)]
        lib.free_network.restype = None

        # clone_network
        lib.clone_network.argtypes = [POINTER(NetworkOpaque)]
        lib.clone_network.restype = POINTER(NetworkOpaque)

        # network_send
        lib.network_send.argtypes = [
            POINTER(NetworkOpaque),  # net_ptr
            c_size_t,                # recipient_id
            ByteSlice,               # message
            POINTER(c_size_t),       # sent_size (output)
        ]
        lib.network_send.restype = c_int  # NetworkErrorCode

    def new_client(
        self,
        party_id: int,
        n_parties: int,
        threshold: int,
        instance_id: int,
        inputs: List[int],
        field_kind: FieldKind = FieldKind.BLS12_381_FR
    ) -> POINTER(HoneyBadgerMPCClientOpaque):
        """
        Create a new HoneyBadger MPC client

        Args:
            party_id: This client's party ID
            n_parties: Total number of MPC parties
            threshold: Byzantine fault tolerance threshold
            instance_id: Unique computation instance ID
            inputs: List of input values
            field_kind: Field type (default: BLS12-381)

        Returns:
            Pointer to the HoneyBadger client

        Raises:
            LibraryLoadError: If library not available
            HoneyBadgerError: If client creation fails
        """
        if not self.available:
            raise LibraryLoadError("MPC library not available")

        # Convert inputs to U256 array
        input_count = len(inputs)
        u256_array = (U256 * input_count)()
        for i, value in enumerate(inputs):
            u256_array[i] = U256.from_int(value)

        # Create U256Slice
        inputs_slice = U256Slice()
        inputs_slice.pointer = u256_array
        inputs_slice.len = input_count

        client_ptr = self._lib.new_honey_badger_mpc_client(
            party_id,
            n_parties,
            threshold,
            instance_id,
            inputs_slice,
            input_count,
            field_kind
        )

        if not client_ptr:
            raise HoneyBadgerError(
                "Failed to create HoneyBadger client",
                HoneyBadgerErrorCode.INPUT_ERROR
            )

        return client_ptr

    def process_message(
        self,
        client_ptr: POINTER(HoneyBadgerMPCClientOpaque),
        network_ptr: POINTER(NetworkOpaque),
        message: bytes
    ) -> None:
        """
        Process an incoming HoneyBadger protocol message

        Args:
            client_ptr: HoneyBadger client handle
            network_ptr: Network handle for sending responses
            message: Raw message bytes

        Raises:
            HoneyBadgerError: If processing fails
        """
        if not self.available:
            raise LibraryLoadError("MPC library not available")

        msg_slice = ByteSlice.from_bytes(message)
        result = self._lib.hb_client_process(client_ptr, network_ptr, msg_slice)
        check_hb_error(result, "hb_client_process")

    def get_output(
        self,
        client_ptr: POINTER(HoneyBadgerMPCClientOpaque),
        field_kind: FieldKind = FieldKind.BLS12_381_FR
    ) -> int:
        """
        Get the computation output

        Args:
            client_ptr: HoneyBadger client handle
            field_kind: Field type

        Returns:
            Output value as integer

        Raises:
            HoneyBadgerError: If output not ready or retrieval fails
        """
        if not self.available:
            raise LibraryLoadError("MPC library not available")

        output = U256()
        result = self._lib.hb_client_get_output(
            client_ptr,
            ctypes.byref(output),
            field_kind
        )
        check_hb_error(result, "hb_client_get_output")

        return output.to_int()

    def free_client(
        self,
        client_ptr: POINTER(HoneyBadgerMPCClientOpaque)
    ) -> None:
        """Free HoneyBadger client handle"""
        if self.available and client_ptr:
            self._lib.free_honey_badger_mpc_client(client_ptr)

    def clone_network(
        self,
        network_ptr: POINTER(NetworkOpaque)
    ) -> POINTER(NetworkOpaque):
        """
        Clone a network handle

        Args:
            network_ptr: Network handle to clone

        Returns:
            New network handle (must be freed separately)
        """
        if not self.available:
            raise LibraryLoadError("MPC library not available")

        return self._lib.clone_network(network_ptr)

    def free_network(self, network_ptr: POINTER(NetworkOpaque)) -> None:
        """Free network handle"""
        if self.available and network_ptr:
            self._lib.free_network(network_ptr)


# Global singleton instance
_hb_client_ffi: Optional[HoneyBadgerClientFFI] = None


def get_hb_client_ffi() -> HoneyBadgerClientFFI:
    """Get the HoneyBadger client FFI singleton"""
    global _hb_client_ffi
    if _hb_client_ffi is None:
        _hb_client_ffi = HoneyBadgerClientFFI()
    return _hb_client_ffi


def is_hb_client_available() -> bool:
    """Check if HoneyBadger client FFI is available"""
    return get_hb_client_ffi().available
