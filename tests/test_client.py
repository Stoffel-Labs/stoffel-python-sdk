"""
Tests for StoffelMPCClient
"""

import pytest
import asyncio
from unittest.mock import Mock, patch

from stoffel.client import StoffelMPCClient


class TestStoffelMPCClient:
    """Test StoffelMPCClient class"""
    
    def test_client_creation_direct_nodes(self):
        """Test client creation with direct node configuration"""
        client = StoffelMPCClient({
            "nodes": ["http://node1:9000", "http://node2:9000", "http://node3:9000"],
            "client_id": "test_client",
            "program_id": "test_program"
        })
        
        assert client.client_id == "test_client"
        assert client.program_id == "test_program"
        assert len(client.node_urls) == 3
        assert not client.connected
    
    def test_client_creation_with_coordinator(self):
        """Test client creation with coordinator for metadata"""
        client = StoffelMPCClient({
            "nodes": ["http://node1:9000", "http://node2:9000"],
            "coordinator_url": "http://coordinator:8080",
            "client_id": "test_client",
            "program_id": "test_program"
        })
        
        assert client.client_id == "test_client"
        assert client.program_id == "test_program"
        assert client.coordinator_url == "http://coordinator:8080"
        assert len(client.node_urls) == 2
        assert not client.connected
    
    def test_client_creation_missing_nodes(self):
        """Test client creation with missing nodes"""
        with pytest.raises(ValueError, match="Network config must specify 'nodes'"):
            StoffelMPCClient({
                "coordinator_url": "http://coordinator:8080",
                "client_id": "test_client",
                "program_id": "test_program"
            })
    
    def test_client_creation_missing_config(self):
        """Test client creation with missing configuration"""
        with pytest.raises(ValueError, match="Network config must specify 'nodes'"):
            StoffelMPCClient({
                "client_id": "test_client",
                "program_id": "test_program"
            })
    
    def test_client_creation_missing_program_id(self):
        """Test client creation with missing program_id"""
        with pytest.raises(ValueError, match="program_id must be specified"):
            StoffelMPCClient({
                "nodes": ["http://node1:9000"],
                "client_id": "test_client"
            })
    
    def test_set_private_data(self):
        """Test setting private data"""
        client = StoffelMPCClient({
            "nodes": ["http://node1:9000"],
            "client_id": "test_client",
            "program_id": "test_program"
        })
        
        client.set_private_data("input1", 42)
        client.set_private_data("input2", 17)
        
        assert client.private_inputs["input1"] == 42
        assert client.private_inputs["input2"] == 17
    
    def test_set_private_inputs(self):
        """Test setting multiple private inputs"""
        client = StoffelMPCClient({
            "nodes": ["http://node1:9000"],
            "client_id": "test_client", 
            "program_id": "test_program"
        })
        
        client.set_private_inputs({
            "a": 100,
            "b": 200,
            "c": 300
        })
        
        assert len(client.private_inputs) == 3
        assert client.private_inputs["a"] == 100
        assert client.private_inputs["b"] == 200
        assert client.private_inputs["c"] == 300
    
    def test_is_ready(self):
        """Test readiness check"""
        client = StoffelMPCClient({
            "nodes": ["http://node1:9000"],
            "client_id": "test_client",
            "program_id": "test_program"
        })
        
        # Not ready initially
        assert not client.is_ready()
        
        # Not ready with just connection
        client.connected = True
        assert not client.is_ready()
        
        # Ready with connection and inputs
        client.set_private_data("input", 42)
        assert client.is_ready()
    
    def test_get_connection_status(self):
        """Test connection status"""
        client = StoffelMPCClient({
            "nodes": ["http://node1:9000", "http://node2:9000"],
            "client_id": "test_client",
            "program_id": "test_program"
        })
        
        client.set_private_data("test_input", 123)
        
        status = client.get_connection_status()
        
        assert status["client_id"] == "test_client"
        assert status["program_id"] == "test_program"
        assert status["mpc_nodes_count"] == 2
        assert status["connected"] is False
        assert status["private_inputs_count"] == 1
    
    def test_get_program_info(self):
        """Test program information"""
        client = StoffelMPCClient({
            "nodes": ["http://node1:9000"],
            "client_id": "test_client",
            "program_id": "test_program"
        })
        
        client.set_private_inputs({"a": 1, "b": 2})
        
        info = client.get_program_info()
        
        assert info["program_id"] == "test_program"
        assert set(info["expected_inputs"]) == {"a", "b"}
        assert info["mpc_nodes_available"] == 0  # Not connected
    
    @pytest.mark.asyncio
    async def test_execute_program_not_connected(self):
        """Test executing program when not connected"""
        client = StoffelMPCClient({
            "nodes": ["http://node1:9000"],
            "client_id": "test_client",
            "program_id": "test_program"
        })
        
        client.set_private_data("input", 42)
        
        # Should attempt to connect automatically
        with patch.object(client, 'connect') as mock_connect:
            with patch.object(client, '_create_secret_shares') as mock_create:
                with patch.object(client, '_send_shares_to_nodes') as mock_send:
                    with patch.object(client, '_collect_result_shares_from_nodes') as mock_collect:
                        with patch.object(client, '_reconstruct_final_result') as mock_reconstruct:
                            
                            mock_create.return_value = [b"share1", b"share2"]
                            mock_send.return_value = "exec_123"
                            mock_collect.return_value = {"node1": b"result1", "node2": b"result2"}
                            mock_reconstruct.return_value = 84
                            
                            result = await client.execute_program()
                            
                            mock_connect.assert_called_once()
                            assert result == 84
    
    @pytest.mark.asyncio
    async def test_execute_program_with_inputs(self):
        """Test executing program with inputs in one call"""
        client = StoffelMPCClient({
            "nodes": ["http://node1:9000"],
            "client_id": "test_client",
            "program_id": "test_program"
        })
        
        with patch.object(client, 'execute_program') as mock_execute:
            mock_execute.return_value = 99
            
            result = await client.execute_program_with_inputs({
                "a": 50,
                "b": 49
            })
            
            assert client.private_inputs["a"] == 50
            assert client.private_inputs["b"] == 49
            assert result == 99
            mock_execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_program_no_inputs(self):
        """Test executing program without inputs"""
        client = StoffelMPCClient({
            "nodes": ["http://node1:9000"],
            "client_id": "test_client",
            "program_id": "test_program"
        })
        
        with pytest.raises(ValueError, match="No private inputs provided"):
            await client.execute_program()
    
    @pytest.mark.asyncio
    async def test_disconnect(self):
        """Test disconnecting from network"""
        client = StoffelMPCClient({
            "nodes": ["http://node1:9000"],
            "client_id": "test_client",
            "program_id": "test_program"
        })
        
        client.connected = True
        client.session_id = "test_session"
        
        await client.disconnect()
        
        assert not client.connected
        assert client.session_id is None