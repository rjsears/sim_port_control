"""Tests for Cisco SSH port discovery methods."""

from unittest.mock import MagicMock, patch

from app.services.cisco_ssh import CiscoSSHService


class TestDiscoverPorts:
    """Tests for port discovery parsing."""

    SAMPLE_OUTPUT = """Interface                      Status         Protocol Description
Vl1                            admin down     down
Vl10                           up             up       Network_Management VLAN
Gi1/0/1                        down           down     Private VLAN for CJ01
Gi1/0/7                        admin down     down     Available
Gi1/0/8                        admin down     down     Available
Gi1/0/20                       up             up       Poly Rove R40 Basestation
"""

    def test_parse_discovers_available_ports(self):
        """Should find ports with 'admin down' status and 'Available' description."""
        switch = MagicMock()
        switch.name = "TestSwitch"
        service = CiscoSSHService(switch)

        with patch.object(service, "_connect") as mock_connect:
            mock_conn = MagicMock()
            mock_conn.send_command.return_value = self.SAMPLE_OUTPUT
            mock_connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_connect.return_value.__exit__ = MagicMock(return_value=False)

            ports = service.discover_ports()

        assert len(ports) == 2
        assert ports[0]["port_name"] == "GigabitEthernet1/0/7"
        assert ports[0]["short_name"] == "Gi1/0/7"
        assert ports[0]["description"] == "Available"
        assert ports[1]["short_name"] == "Gi1/0/8"

    def test_excludes_in_use_ports(self):
        """Should not include ports that are up or have non-Available descriptions."""
        switch = MagicMock()
        switch.name = "TestSwitch"
        service = CiscoSSHService(switch)

        with patch.object(service, "_connect") as mock_connect:
            mock_conn = MagicMock()
            mock_conn.send_command.return_value = self.SAMPLE_OUTPUT
            mock_connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_connect.return_value.__exit__ = MagicMock(return_value=False)

            ports = service.discover_ports()

        port_names = [p["short_name"] for p in ports]
        assert "Gi1/0/1" not in port_names  # down but not Available
        assert "Gi1/0/20" not in port_names  # up/up
        assert "Vl1" not in port_names  # VLAN interface


class TestVerifyPortState:
    """Tests for port state verification."""

    ADMIN_DOWN_OUTPUT = """GigabitEthernet1/0/7 is administratively down, line protocol is down (disabled)
  Hardware is Gigabit Ethernet, address is 0022.56aa.8907
  Description: Available
  MTU 1500 bytes"""

    ENABLED_NO_LINK_OUTPUT = """GigabitEthernet1/0/7 is down, line protocol is down (notconnect)
  Hardware is Gigabit Ethernet, address is 0022.56aa.8907
  Description: SIMPORT:CJ3
  MTU 1500 bytes"""

    ENABLED_CONNECTED_OUTPUT = """GigabitEthernet1/0/7 is up, line protocol is up (connected)
  Hardware is Gigabit Ethernet, address is 0022.56aa.8907
  Description: SIMPORT:CJ3
  MTU 1500 bytes"""

    def test_detects_administratively_down(self):
        """Should detect administratively down state."""
        switch = MagicMock()
        service = CiscoSSHService(switch)

        with patch.object(service, "_connect") as mock_connect:
            mock_conn = MagicMock()
            mock_conn.send_command.return_value = self.ADMIN_DOWN_OUTPUT
            mock_connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_connect.return_value.__exit__ = MagicMock(return_value=False)

            state = service.verify_port_state("Gi1/0/7")

        assert state["is_admin_down"] is True
        assert state["description"] == "Available"

    def test_detects_enabled_no_link(self):
        """Should detect enabled port with no link."""
        switch = MagicMock()
        service = CiscoSSHService(switch)

        with patch.object(service, "_connect") as mock_connect:
            mock_conn = MagicMock()
            mock_conn.send_command.return_value = self.ENABLED_NO_LINK_OUTPUT
            mock_connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_connect.return_value.__exit__ = MagicMock(return_value=False)

            state = service.verify_port_state("Gi1/0/7")

        assert state["is_admin_down"] is False
        assert state["description"] == "SIMPORT:CJ3"

    def test_detects_enabled_connected(self):
        """Should detect enabled and connected port."""
        switch = MagicMock()
        service = CiscoSSHService(switch)

        with patch.object(service, "_connect") as mock_connect:
            mock_conn = MagicMock()
            mock_conn.send_command.return_value = self.ENABLED_CONNECTED_OUTPUT
            mock_connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_connect.return_value.__exit__ = MagicMock(return_value=False)

            state = service.verify_port_state("Gi1/0/7")

        assert state["is_admin_down"] is False
        assert state["is_connected"] is True


class TestConfigurePort:
    """Tests for port configuration commands."""

    def test_assign_port_sends_correct_commands(self):
        """Should send full configuration sequence for assignment."""
        switch = MagicMock()
        service = CiscoSSHService(switch)

        with patch.object(service, "_connect") as mock_connect:
            mock_conn = MagicMock()
            mock_conn.send_config_set.return_value = "config output"
            mock_conn.send_command.return_value = "write ok"
            mock_connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_connect.return_value.__exit__ = MagicMock(return_value=False)

            service.configure_port_assign("Gi1/0/7", "CJ3", 30)

        mock_conn.send_config_set.assert_called_once()
        commands = mock_conn.send_config_set.call_args[0][0]
        assert "interface Gi1/0/7" in commands
        assert "description SIMPORT:CJ3" in commands
        assert "switchport" in commands
        assert "switchport mode access" in commands
        assert "switchport access vlan 30" in commands
        # Note: Port stays shutdown after assignment - user enables explicitly

    def test_release_port_sends_correct_commands(self):
        """Should reset port to Available state."""
        switch = MagicMock()
        service = CiscoSSHService(switch)

        with patch.object(service, "_connect") as mock_connect:
            mock_conn = MagicMock()
            mock_conn.send_config_set.return_value = "config output"
            mock_conn.send_command.return_value = "write ok"
            mock_connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_connect.return_value.__exit__ = MagicMock(return_value=False)

            service.configure_port_release("Gi1/0/7", 30)

        mock_conn.send_config_set.assert_called_once()
        commands = mock_conn.send_config_set.call_args[0][0]
        assert "interface Gi1/0/7" in commands
        assert "description Available" in commands
        assert "no switchport access vlan 30" in commands
        assert "shutdown" in commands
