"""
Tests for CiscoSSH service with mocked network operations.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.models.switch import Switch
from app.services.cisco_ssh import CiscoSSHError, CiscoSSHService
from app.services.encryption import EncryptionService


@pytest.fixture
def mock_switch():
    """Create a mock switch object."""
    encryption = EncryptionService()
    switch = MagicMock(spec=Switch)
    switch.ip_address = "192.168.1.1"
    switch.username = "admin"
    switch.password_encrypted = encryption.encrypt("switchpass")
    switch.device_type = "cisco_ios"
    switch.name = "Test Switch"
    return switch


@pytest.fixture
def mock_connection():
    """Create a mock Netmiko connection."""
    conn = MagicMock()
    conn.send_command.return_value = "Cisco IOS Software"
    conn.send_config_set.return_value = ""
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    return conn


@pytest.mark.asyncio
class TestCiscoSSHService:
    """Tests for CiscoSSHService."""

    @patch.object(CiscoSSHService, "_connect")
    async def test_test_connection_success(self, mock_connect_method, mock_switch, mock_connection):
        """Should test connection successfully."""
        mock_connect_method.return_value = mock_connection

        service = CiscoSSHService(mock_switch)
        result = await service.test_connection_async()

        assert result is not None
        assert "connected" in result
        assert result["connected"] is True

    @patch.object(CiscoSSHService, "_connect")
    async def test_test_connection_failure(self, mock_connect_method, mock_switch):
        """Should raise error on connection failure."""
        mock_connect_method.side_effect = CiscoSSHError("Connection refused")

        service = CiscoSSHService(mock_switch)

        with pytest.raises(CiscoSSHError) as exc_info:
            await service.test_connection_async()

        assert "Connection" in str(exc_info.value)

    @patch.object(CiscoSSHService, "_connect")
    async def test_enable_port_success(self, mock_connect_method, mock_switch, mock_connection):
        """Should enable port successfully."""
        mock_connect_method.return_value = mock_connection

        service = CiscoSSHService(mock_switch)
        result = await service.enable_port_async("Gi0/1", vlan=30)

        assert result is True
        mock_connection.send_config_set.assert_called_once()
        config_commands = mock_connection.send_config_set.call_args[0][0]
        assert "interface Gi0/1" in config_commands
        assert "no shutdown" in config_commands

    @patch.object(CiscoSSHService, "_connect")
    async def test_enable_port_with_vlan(self, mock_connect_method, mock_switch, mock_connection):
        """Should enable port with VLAN configuration."""
        mock_connect_method.return_value = mock_connection

        service = CiscoSSHService(mock_switch)
        await service.enable_port_async("Gi0/1", vlan=50)

        config_commands = mock_connection.send_config_set.call_args[0][0]
        assert "switchport access vlan 50" in config_commands

    @patch.object(CiscoSSHService, "_connect")
    async def test_disable_port_success(self, mock_connect_method, mock_switch, mock_connection):
        """Should disable port successfully."""
        mock_connect_method.return_value = mock_connection

        service = CiscoSSHService(mock_switch)
        result = await service.disable_port_async("Gi0/1")

        assert result is True
        mock_connection.send_config_set.assert_called_once()
        config_commands = mock_connection.send_config_set.call_args[0][0]
        assert "interface Gi0/1" in config_commands
        assert "shutdown" in config_commands

    @patch.object(CiscoSSHService, "_connect")
    async def test_enable_port_connection_error(self, mock_connect_method, mock_switch):
        """Should raise error on enable connection failure."""
        mock_connect_method.side_effect = CiscoSSHError("Connection refused")

        service = CiscoSSHService(mock_switch)

        with pytest.raises(CiscoSSHError):
            await service.enable_port_async("Gi0/1", vlan=30)

    @patch.object(CiscoSSHService, "_connect")
    async def test_disable_port_connection_error(self, mock_connect_method, mock_switch):
        """Should raise error on disable connection failure."""
        mock_connect_method.side_effect = CiscoSSHError("Connection refused")

        service = CiscoSSHService(mock_switch)

        with pytest.raises(CiscoSSHError):
            await service.disable_port_async("Gi0/1")

    @patch.object(CiscoSSHService, "_connect")
    async def test_get_port_status(self, mock_connect_method, mock_switch, mock_connection):
        """Should get port status."""
        mock_connection.send_command.return_value = """
Interface    IP-Address  OK? Method Status   Protocol
Gi0/1        unassigned  YES unset  up       up
        """
        mock_connect_method.return_value = mock_connection

        service = CiscoSSHService(mock_switch)
        result = await service.get_port_status_async("Gi0/1")

        assert result is not None
        mock_connection.send_command.assert_called()

    @patch.object(CiscoSSHService, "_connect")
    async def test_discover_ports(self, mock_connect_method, mock_switch, mock_connection):
        """Should discover available ports."""
        mock_connection.send_command.return_value = """
Interface              Status         Protocol Description
Gi0/1                  up             up       User Port 1
Gi0/2                  down           down     User Port 2
Gi0/3                  admin down     down     Disabled Port
        """
        mock_connect_method.return_value = mock_connection

        service = CiscoSSHService(mock_switch)
        result = await service.discover_ports_async()

        assert result is not None
        assert isinstance(result, list)


class TestCiscoSSHServiceSync:
    """Tests for synchronous CiscoSSHService methods."""

    def test_password_decryption(self, mock_switch):
        """Should decrypt switch password."""
        encryption = EncryptionService()
        decrypted = encryption.decrypt(mock_switch.password_encrypted)
        assert decrypted == "switchpass"

    def test_service_initialization(self, mock_switch):
        """Should initialize service with switch."""
        service = CiscoSSHService(mock_switch)

        assert service.switch == mock_switch

    @patch.object(CiscoSSHService, "_connect")
    def test_test_connection_sync(self, mock_connect_method, mock_switch, mock_connection):
        """Should test connection synchronously."""
        mock_connect_method.return_value = mock_connection

        service = CiscoSSHService(mock_switch)
        result = service.test_connection()

        assert result is not None
        assert "connected" in result

    @patch.object(CiscoSSHService, "_connect")
    def test_enable_port_sync(self, mock_connect_method, mock_switch, mock_connection):
        """Should enable port synchronously."""
        mock_connect_method.return_value = mock_connection

        service = CiscoSSHService(mock_switch)
        result = service.enable_port("Gi0/1", vlan=30)

        assert result is True

    @patch.object(CiscoSSHService, "_connect")
    def test_disable_port_sync(self, mock_connect_method, mock_switch, mock_connection):
        """Should disable port synchronously."""
        mock_connect_method.return_value = mock_connection

        service = CiscoSSHService(mock_switch)
        result = service.disable_port("Gi0/1")

        assert result is True


class TestCiscoSSHError:
    """Tests for CiscoSSHError exception."""

    def test_error_message(self):
        """Should store error message."""
        error = CiscoSSHError("Test error message")
        assert str(error) == "Test error message"

    def test_error_inheritance(self):
        """Should be an Exception."""
        error = CiscoSSHError("Test")
        assert isinstance(error, Exception)
