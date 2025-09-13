"""
Stoffel MPC Network Client

This module provides a client for connecting to and interacting with the Stoffel
MPC network. The client handles private data secret sharing, network communication,
and result reconstruction in a client-server model.
"""

from typing import Any, Dict, List, Optional, Union
import asyncio
import logging


logger = logging.getLogger(__name__)


class StoffelClient:
    """
    Client for Stoffel MPC network operations
    
    Handles client interaction with the MPC network:
    - Connect to MPC network nodes (depending on deployment configuration)
    - Manage private data and secret sharing
    - Send shares to MPC network running a specific program
    - Receive shares from each MPC node and reconstruct final result
    """
    
    def __init__(self, network_config: Dict[str, Any]):
        """
        Initialize Stoffel client for MPC network operations
        
        Args:
            network_config: Configuration for connecting to MPC network
                          {
                              "nodes": ["http://node1:8080", "http://node2:8080", "http://node3:8080"],
                              "client_id": "client_001", 
                              "program_id": "secure_addition_v1"
                          }
                          OR (with coordinator for metadata):
                          {
                              "nodes": ["http://node1:8080", "http://node2:8080", "http://node3:8080"],
                              "coordinator_url": "http://coordinator:8080",  # Optional: for metadata exchange
                              "client_id": "client_001",
                              "program_id": "secure_addition_v1"
                          }
        """
        self.network_config = network_config
        self.client_id = network_config.get("client_id", "default_client")
        
        # MPC nodes are required - client always needs to know where to connect
        self.node_urls = network_config.get("nodes", [])
        if not self.node_urls:
            raise ValueError("Network config must specify 'nodes' - MPC network nodes are required")
        
        # Optional coordinator for metadata exchange (not for discovery)
        self.coordinator_url = network_config.get("coordinator_url")
        
        # The MPC network is pre-configured to run this specific program
        self.program_id = network_config.get("program_id")
        if not self.program_id:
            raise ValueError("program_id must be specified - MPC network runs a specific program")
        
        self.connected = False
        self.private_inputs = {}  # Legacy support
        self.secret_inputs = {}   # New: explicitly secret inputs 
        self.public_inputs = {}   # New: explicitly public inputs
        self.session_id = None
        
        logger.info(f"Initialized MPC client {self.client_id} for program {self.program_id}")
        logger.info(f"MPC nodes: {len(self.node_urls)}")
        if self.coordinator_url:
            logger.info(f"Coordinator available for metadata: {self.coordinator_url}")
    
    async def connect(self) -> None:
        """
        Connect to the MPC network
        
        The coordinator (if present) is used for metadata exchange, not discovery.
        The client connects directly to known MPC nodes for computation.
        """
        try:
            # Step 1: Exchange metadata with coordinator if configured
            if self.coordinator_url:
                logger.info(f"Exchanging metadata with coordinator")
                await self._exchange_metadata_with_coordinator()
            
            logger.info(f"Connecting to {len(self.node_urls)} MPC network nodes")
            
            # Step 2: Connect to the MPC network nodes
            await self._connect_to_mpc_nodes()
            
            self.connected = True
            self.session_id = f"session_{self.client_id}"
            
            logger.info(f"Connected to MPC network running program {self.program_id}")
            
        except Exception as e:
            logger.error(f"Failed to connect to MPC network: {e}")
            raise ConnectionError(f"MPC network connection failed: {e}")
    
    def set_private_data(self, name: str, value: Any) -> None:
        """
        Set private data that will be secret shared and sent to MPC network
        
        Args:
            name: Identifier for the private input
            value: The private value to be secret shared
        """
        self.private_inputs[name] = value
        logger.debug(f"Set private input '{name}' = {value}")
    
    def set_private_inputs(self, inputs: Dict[str, Any]) -> None:
        """
        Set multiple private inputs at once (legacy method)
        
        Args:
            inputs: Dictionary mapping input names to private values
        """
        self.private_inputs.update(inputs)
        logger.debug(f"Set {len(inputs)} private inputs")
    
    def set_secret_input(self, name: str, value: Any) -> None:
        """
        Set a secret input that will be secret shared across MPC nodes
        
        Args:
            name: Identifier for the secret input
            value: The secret value to be shared
        """
        self.secret_inputs[name] = value
        logger.debug(f"Set secret input '{name}' = <hidden>")
    
    def set_public_input(self, name: str, value: Any) -> None:
        """
        Set a public input that will be visible to all MPC nodes
        
        Args:
            name: Identifier for the public input  
            value: The public value (visible to all nodes)
        """
        self.public_inputs[name] = value
        logger.debug(f"Set public input '{name}' = {value}")
    
    def set_inputs(self, secret_inputs: Optional[Dict[str, Any]] = None, 
                   public_inputs: Optional[Dict[str, Any]] = None) -> None:
        """
        Set multiple secret and public inputs at once
        
        Args:
            secret_inputs: Dictionary mapping input names to secret values
            public_inputs: Dictionary mapping input names to public values
        """
        if secret_inputs:
            self.secret_inputs.update(secret_inputs)
            logger.debug(f"Set {len(secret_inputs)} secret inputs")
        if public_inputs:
            self.public_inputs.update(public_inputs)
            logger.debug(f"Set {len(public_inputs)} public inputs: {list(public_inputs.keys())}")
    
    async def execute_program(self, inputs: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute the pre-configured program on the MPC network with private inputs
        
        The MPC network is already configured to run a specific program.
        This method sends the client's private inputs and retrieves the result.
        
        Args:
            inputs: Private inputs for this client (optional, uses set inputs if None)
            
        Returns:
            The final computation result (reconstructed from shares)
        """
        if not self.connected:
            await self.connect()
        
        # Use provided inputs or previously set inputs
        if inputs:
            self.private_inputs.update(inputs)
        
        # Check if we have any inputs (legacy private_inputs or new secret/public inputs)
        has_legacy_inputs = bool(self.private_inputs)
        has_new_inputs = bool(self.secret_inputs) or bool(self.public_inputs)
        
        if not (has_legacy_inputs or has_new_inputs):
            raise ValueError("No inputs provided. Use set_secret_input(), set_public_input(), or legacy methods.")
        
        try:
            logger.info(f"Executing program {self.program_id} with inputs")
            
            # Handle different input types
            all_secret_shares = {}
            all_public_data = {}
            
            # Legacy private inputs (treat as secret)
            if self.private_inputs:
                logger.debug("Processing legacy private inputs as secret")
                for name, value in self.private_inputs.items():
                    shares = await self._create_secret_shares(value)
                    all_secret_shares[name] = shares
                    logger.debug(f"Created secret shares for legacy input '{name}'")
            
            # New explicit secret inputs
            if self.secret_inputs:
                logger.debug("Processing explicit secret inputs")
                for name, value in self.secret_inputs.items():
                    shares = await self._create_secret_shares(value)
                    all_secret_shares[name] = shares
                    logger.debug(f"Created secret shares for secret input '{name}'")
            
            # New explicit public inputs (no secret sharing needed)
            if self.public_inputs:
                logger.debug("Processing explicit public inputs")
                for name, value in self.public_inputs.items():
                    all_public_data[name] = value
                    logger.debug(f"Prepared public input '{name}' = {value}")
            
            # Send data to MPC network nodes
            execution_id = await self._send_data_to_nodes(all_secret_shares, all_public_data)
            
            logger.info(f"Data sent to MPC network, execution ID: {execution_id}")
            
            # Wait for computation completion and collect result shares from nodes
            result_shares_from_nodes = await self._collect_result_shares_from_nodes(execution_id)
            
            # Reconstruct final result from shares received from each node
            final_result = await self._reconstruct_final_result(result_shares_from_nodes)
            
            logger.info(f"Program execution completed, result: {final_result}")
            return final_result
            
        except Exception as e:
            logger.error(f"Failed to execute program: {e}")
            raise RuntimeError(f"Program execution failed: {e}")
    
    async def disconnect(self) -> None:
        """
        Disconnect from the MPC network
        """
        if self.connected:
            logger.info("Disconnecting from MPC network")
            # Cleanup network connections
            self.connected = False
            self.session_id = None
    
    async def _create_secret_shares(self, value: Any) -> List[bytes]:
        """
        Create secret shares for a private value
        
        Args:
            value: Private value to secret share
            
        Returns:
            List of secret share bytes
        """
        # This would use the actual secret sharing scheme
        # For now, simulate share creation
        await asyncio.sleep(0.01)
        
        # Placeholder: create dummy shares
        num_parties = self.network_config.get("num_parties", 3)
        shares = [f"share_{i}_{value}".encode() for i in range(num_parties)]
        
        return shares
    
    async def _exchange_metadata_with_coordinator(self) -> None:
        """
        Exchange application metadata with coordinator (skeleton implementation)
        
        The coordinator is primarily for MPC network orchestration. Client interaction
        is limited to exchanging extra metadata related to the application when needed.
        This functionality is still in development.
        """
        logger.debug(f"Exchanging metadata with coordinator for program {self.program_id}")
        
        # Skeleton: This would make actual HTTP calls to exchange metadata
        # Example metadata exchange:
        # 1. Send application-specific metadata to coordinator
        # 2. Receive coordinator response with any additional context needed
        
        # await http_client.post(f"{self.coordinator_url}/metadata", {
        #     "client_id": self.client_id,
        #     "program_id": self.program_id,
        #     "application_metadata": {...},  # App-specific context
        # })
        # 
        # coordinator_response = await http_client.get(f"{self.coordinator_url}/context/{self.client_id}")
        # # Process any context/metadata returned by coordinator
        
        await asyncio.sleep(0.05)  # Simulate metadata exchange
        logger.debug("Metadata exchange with coordinator completed")
    
    async def _connect_to_mpc_nodes(self) -> None:
        """
        Establish connections to MPC network nodes
        
        This is where the actual MPC computation will happen.
        """
        for node_url in self.node_urls:
            # Connect to each MPC network node
            await asyncio.sleep(0.05)  # Simulate connection time
            logger.debug(f"Connected to MPC network node: {node_url}")
    
    async def _send_data_to_nodes(self, secret_shares: Dict[str, List[bytes]], 
                                  public_data: Dict[str, Any]) -> str:
        """
        Send secret shares and public data to each MPC node
        
        Args:
            secret_shares: Dictionary of secret shares to distribute
            public_data: Dictionary of public data (visible to all nodes)
            
        Returns:
            Execution ID for tracking this computation
        """
        execution_id = f"exec_{self.program_id}_{self.session_id}"
        
        # Send data to each node
        for i, node_url in enumerate(self.node_urls):
            node_shares = {}
            
            # Each node gets different secret shares
            for name, shares_list in secret_shares.items():
                if i < len(shares_list):
                    node_shares[name] = shares_list[i]
            
            # All nodes get the same public data
            node_public_data = public_data.copy()
            
            # Send this node's shares and public data
            await self._send_data_to_node(node_url, execution_id, node_shares, node_public_data)
            logger.debug(f"Sent data to node {i+1}: {node_url}")
        
        return execution_id
    
    async def _send_shares_to_nodes(self, secret_shares: Dict[str, List[bytes]]) -> str:
        """
        Send secret shares to each MPC node
        
        Args:
            secret_shares: Dictionary of secret shares to distribute
            
        Returns:
            Execution ID for tracking this computation
        """
        execution_id = f"exec_{self.program_id}_{self.session_id}"
        
        # Send shares to each node (each node gets different shares)
        for i, node_url in enumerate(self.node_urls):
            node_shares = {}
            for name, shares_list in secret_shares.items():
                if i < len(shares_list):
                    node_shares[name] = shares_list[i]  # Each node gets its share
            
            # Send this node's shares
            await self._send_shares_to_node(node_url, execution_id, node_shares)
            logger.debug(f"Sent shares to node {i+1}: {node_url}")
        
        return execution_id
    
    async def _send_data_to_node(self, node_url: str, execution_id: str, 
                                 shares: Dict[str, bytes], public_data: Dict[str, Any]) -> None:
        """
        Send shares and public data to a specific MPC node
        
        Args:
            node_url: URL of the MPC node
            execution_id: Execution ID
            shares: Secret shares to send to this node
            public_data: Public data visible to this node
        """
        # This would make actual HTTP/network call to the node
        await asyncio.sleep(0.1)  # Simulate network time
        
        # Skeleton: When backend supports public/secret distinction, this would send:
        # response = await http_client.post(f"{node_url}/execute", {
        #     "execution_id": execution_id,
        #     "program_id": self.program_id,
        #     "client_id": self.client_id,
        #     "secret_shares": shares,      # Only this node's shares
        #     "public_inputs": public_data  # Same for all nodes
        # })
    
    async def _send_shares_to_node(self, node_url: str, execution_id: str, shares: Dict[str, bytes]) -> None:
        """
        Send shares to a specific MPC node (legacy method)
        
        Args:
            node_url: URL of the MPC node
            execution_id: Execution ID
            shares: Shares to send to this node
        """
        # This would make actual HTTP/network call to the node
        await asyncio.sleep(0.1)  # Simulate network time
        
        # Placeholder for actual network call:
        # response = await http_client.post(f"{node_url}/execute", {
        #     "execution_id": execution_id,
        #     "program_id": self.program_id,
        #     "client_id": self.client_id,
        #     "shares": shares
        # })
    
    async def _collect_result_shares_from_nodes(self, execution_id: str) -> Dict[str, bytes]:
        """
        Collect result shares from each MPC node after computation completion
        
        Args:
            execution_id: Execution ID to query for
            
        Returns:
            Dictionary mapping node_url to result share from that node
        """
        result_shares_from_nodes = {}
        
        # Poll each node for its result share
        for node_url in self.node_urls:
            node_result_share = await self._get_result_share_from_node(node_url, execution_id)
            result_shares_from_nodes[node_url] = node_result_share
            logger.debug(f"Collected result share from {node_url}")
        
        return result_shares_from_nodes
    
    async def _get_result_share_from_node(self, node_url: str, execution_id: str) -> bytes:
        """
        Get result share from a specific MPC node
        
        Args:
            node_url: URL of the MPC node
            execution_id: Execution ID
            
        Returns:
            Result share bytes from this node
        """
        # Poll this node until computation is complete
        max_attempts = 30
        for attempt in range(max_attempts):
            await asyncio.sleep(1.0)  # Wait between polls
            
            # This would make actual HTTP call to check status and get result
            # response = await http_client.get(f"{node_url}/result/{execution_id}")
            
            if attempt >= 5:  # Simulate completion after 5 seconds
                # Return the result share from this node
                return f"result_share_from_{node_url}_{execution_id}".encode()
        
        raise TimeoutError(f"Node {node_url} did not complete execution {execution_id} in time")
    
    async def _reconstruct_final_result(self, result_shares_from_nodes: Dict[str, bytes]) -> Any:
        """
        Reconstruct the final clear result from shares received from each MPC node
        
        Args:
            result_shares_from_nodes: Dictionary of node_url -> result_share_bytes
            
        Returns:
            The reconstructed clear result value
        """
        logger.info(f"Reconstructing result from {len(result_shares_from_nodes)} node shares")
        
        # This would perform actual share reconstruction using threshold secret sharing
        # The reconstruction algorithm depends on the MPC protocol (Shamir, etc.)
        await asyncio.sleep(0.1)  # Simulate reconstruction time
        
        # Placeholder: simulate result reconstruction
        # In reality, this would:
        # 1. Validate we have enough shares (>= threshold)
        # 2. Use the secret sharing scheme to reconstruct the clear value
        # 3. Handle different data types (int, float, etc.)
        
        shares = list(result_shares_from_nodes.values())
        logger.debug(f"Reconstructing from shares: {len(shares)} nodes")
        
        # Simulated reconstruction - return placeholder result
        reconstructed_value = 42  # This would be the actual reconstructed result
        
        logger.info(f"Successfully reconstructed final result: {reconstructed_value}")
        return reconstructed_value
    
    def get_connection_status(self) -> Dict[str, Any]:
        """
        Get current connection status and session info
        
        Returns:
            Status information dictionary
        """
        return {
            "connected": self.connected,
            "client_id": self.client_id,
            "program_id": self.program_id,
            "coordinator_url": self.coordinator_url,
            "mpc_nodes_count": len(self.node_urls),
            "session_id": self.session_id,
            "private_inputs_count": len(self.private_inputs)
        }
    
    async def execute_program_with_inputs(self, inputs: Dict[str, Any]) -> Any:
        """
        Convenience method: set inputs and execute program in one call (legacy)
        
        Args:
            inputs: Private inputs for this client
            
        Returns:
            The final computation result
        """
        self.set_private_inputs(inputs)
        return await self.execute_program()
    
    async def execute_with_inputs(self, secret_inputs: Optional[Dict[str, Any]] = None,
                                  public_inputs: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute program with explicit secret and public inputs in one call
        
        Args:
            secret_inputs: Dictionary mapping input names to secret values
            public_inputs: Dictionary mapping input names to public values
            
        Returns:
            The final computation result
        """
        self.set_inputs(secret_inputs, public_inputs)
        return await self.execute_program()
    
    def is_ready(self) -> bool:
        """
        Check if the client is ready to execute programs
        
        Returns:
            True if connected and has inputs set (legacy private_inputs or new secret/public inputs)
        """
        has_inputs = bool(self.private_inputs) or bool(self.secret_inputs) or bool(self.public_inputs)
        return self.connected and has_inputs
    
    def get_program_info(self) -> Dict[str, Any]:
        """
        Get information about the program this client is configured for
        
        Returns:
            Program information
        """
        # Combine all input types for expected_inputs (for backward compatibility)
        all_inputs = set(self.private_inputs.keys()) | set(self.secret_inputs.keys()) | set(self.public_inputs.keys())
        
        return {
            "program_id": self.program_id,
            "expected_inputs": list(all_inputs),
            "secret_inputs": list(self.secret_inputs.keys()),
            "public_inputs": list(self.public_inputs.keys()),
            "mpc_nodes_available": len(self.node_urls) if self.connected else 0
        }
