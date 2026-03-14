# Port Discovery Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add automatic port discovery to prevent accidental misconfiguration of switch ports by only allowing assignment of discovered "Available" ports.

**Architecture:** New DiscoveredPort model tracks ports found on switches. CiscoSSHService gains discovery and verification methods. PortDiscoveryService orchestrates scanning, assignment, and release operations. Frontend shows color-coded port status with interactive enable/disable.

**Tech Stack:** FastAPI, SQLAlchemy (async), Netmiko, Vue 3, Pinia, TailwindCSS

**Spec:** `docs/superpowers/specs/2026-03-10-port-discovery-design.md`

---

## File Structure

### New Files
| File | Responsibility |
|------|----------------|
| `backend/app/models/discovered_port.py` | DiscoveredPort SQLAlchemy model |
| `backend/app/schemas/discovery.py` | Pydantic schemas for discovery endpoints |
| `backend/app/services/port_discovery.py` | Port discovery and assignment orchestration |
| `backend/app/routers/discovery.py` | API endpoints for scanning and port management |
| `backend/alembic/versions/002_discovered_ports.py` | Database migration |
| `backend/tests/test_discovery.py` | Tests for discovery service |
| `backend/tests/test_discovery_api.py` | Tests for discovery API endpoints |
| `frontend/src/components/PortLegend.vue` | Color legend footer component |
| `frontend/src/components/PortStatusBadge.vue` | Reusable port status indicator |

### Modified Files
| File | Changes |
|------|---------|
| `backend/app/services/cisco_ssh.py` | Add `discover_ports()`, `assign_port()`, `release_port()`, `verify_port_state()` |
| `backend/app/models/port_assignment.py` | Add `discovered_port_id` FK |
| `backend/app/models/__init__.py` | Export DiscoveredPort |
| `backend/app/routers/switches.py` | Trigger scan on switch add |
| `backend/app/main.py` | Include discovery router |
| `frontend/src/views/SimulatorDetailView.vue` | Updated colors and interactions |
| `frontend/src/services/api.js` | Add discovery API methods |
| `frontend/src/stores/simulators.js` | Handle new port states |

---

## Chunk 1: Database Model & Migration

### Task 1.1: Create DiscoveredPort Model

**Files:**
- Create: `backend/app/models/discovered_port.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Create the DiscoveredPort model file**

```python
# backend/app/models/discovered_port.py
"""
Discovered port model for tracking switch ports found during scanning.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Literal

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.port_assignment import PortAssignment
    from app.models.switch import Switch

DiscoveredPortStatus = Literal["available", "assigned", "error", "in_use"]


class DiscoveredPort(Base):
    """A port discovered on a switch during scanning."""

    __tablename__ = "discovered_ports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    switch_id: Mapped[int] = mapped_column(
        ForeignKey("switches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    port_name: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "GigabitEthernet1/0/7"
    short_name: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g., "Gi1/0/7"
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="available")
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    switch: Mapped["Switch"] = relationship("Switch", back_populates="discovered_ports")
    port_assignment: Mapped["PortAssignment | None"] = relationship(
        "PortAssignment", back_populates="discovered_port", uselist=False
    )

    @property
    def is_available(self) -> bool:
        """Check if port can be assigned."""
        return self.status == "available"

    @property
    def is_assigned(self) -> bool:
        """Check if port is assigned to a simulator."""
        return self.status == "assigned"

    def __repr__(self) -> str:
        return f"<DiscoveredPort(id={self.id}, port='{self.short_name}', status='{self.status}')>"
```

- [ ] **Step 2: Update models __init__.py**

Add to `backend/app/models/__init__.py`:

```python
from app.models.discovered_port import DiscoveredPort
```

And add "DiscoveredPort" to the `__all__` list (alphabetically sorted).

- [ ] **Step 3: Verify syntax**

Run: `python3 -m py_compile backend/app/models/discovered_port.py`
Expected: No output (success)

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/discovered_port.py backend/app/models/__init__.py
git commit -m "feat: add DiscoveredPort model"
```

### Task 1.2: Update Switch Model with Relationship

**Files:**
- Modify: `backend/app/models/switch.py`

- [ ] **Step 1: Add relationship to Switch model**

Add to imports in `backend/app/models/switch.py`:
```python
if TYPE_CHECKING:
    from app.models.discovered_port import DiscoveredPort
```

Add relationship after `port_assignments`:
```python
    discovered_ports: Mapped[list["DiscoveredPort"]] = relationship(
        "DiscoveredPort", back_populates="switch", cascade="all, delete-orphan"
    )
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/models/switch.py
git commit -m "feat: add discovered_ports relationship to Switch"
```

### Task 1.3: Update PortAssignment Model

**Files:**
- Modify: `backend/app/models/port_assignment.py`

- [ ] **Step 1: Add discovered_port_id FK**

Add to imports:
```python
if TYPE_CHECKING:
    from app.models.discovered_port import DiscoveredPort
```

Add column after `switch_id`:
```python
    discovered_port_id: Mapped[int | None] = mapped_column(
        ForeignKey("discovered_ports.id", ondelete="SET NULL"), nullable=True, index=True
    )
```

Add relationship:
```python
    discovered_port: Mapped["DiscoveredPort | None"] = relationship(
        "DiscoveredPort", back_populates="port_assignment"
    )
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/models/port_assignment.py
git commit -m "feat: add discovered_port_id to PortAssignment"
```

### Task 1.4: Create Database Migration

**Files:**
- Create: `backend/alembic/versions/002_discovered_ports.py`

- [ ] **Step 1: Create migration file**

```python
# backend/alembic/versions/002_discovered_ports.py
"""Add discovered_ports table and link to port_assignments.

Revision ID: 002
Revises: 001
Create Date: 2026-03-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "discovered_ports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("switch_id", sa.Integer(), nullable=False),
        sa.Column("port_name", sa.String(50), nullable=False),
        sa.Column("short_name", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="available"),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("discovered_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.ForeignKeyConstraint(["switch_id"], ["switches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_discovered_ports_switch_id", "discovered_ports", ["switch_id"])
    op.create_index("ix_discovered_ports_status", "discovered_ports", ["status"])

    op.add_column(
        "port_assignments",
        sa.Column("discovered_port_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_port_assignments_discovered_port",
        "port_assignments",
        "discovered_ports",
        ["discovered_port_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_port_assignments_discovered_port_id", "port_assignments", ["discovered_port_id"])


def downgrade() -> None:
    op.drop_index("ix_port_assignments_discovered_port_id", table_name="port_assignments")
    op.drop_constraint("fk_port_assignments_discovered_port", "port_assignments", type_="foreignkey")
    op.drop_column("port_assignments", "discovered_port_id")
    op.drop_index("ix_discovered_ports_status", table_name="discovered_ports")
    op.drop_index("ix_discovered_ports_switch_id", table_name="discovered_ports")
    op.drop_table("discovered_ports")
```

- [ ] **Step 2: Verify syntax**

Run: `python3 -m py_compile backend/alembic/versions/002_discovered_ports.py`
Expected: No output (success)

- [ ] **Step 3: Commit**

```bash
git add backend/alembic/versions/002_discovered_ports.py
git commit -m "feat: add migration for discovered_ports table"
```

---

## Chunk 2: Cisco SSH Discovery Methods

### Task 2.1: Add Port Discovery to CiscoSSHService

**Files:**
- Modify: `backend/app/services/cisco_ssh.py`
- Create: `backend/tests/test_cisco_ssh_discovery.py`

- [ ] **Step 1: Write failing test for discover_ports**

Create `backend/tests/test_cisco_ssh_discovery.py`:

```python
"""Tests for Cisco SSH port discovery methods."""

from unittest.mock import MagicMock, patch

import pytest

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_cisco_ssh_discovery.py -v`
Expected: FAIL with "AttributeError: 'CiscoSSHService' object has no attribute 'discover_ports'"

- [ ] **Step 3: Implement discover_ports method**

Add to `backend/app/services/cisco_ssh.py` after `get_port_status`:

```python
    def discover_ports(self) -> list[dict[str, Any]]:
        """
        Discover available ports on the switch.

        Runs 'sh int description' and parses for ports that are:
        - Administratively down (admin down)
        - Have description 'Available'

        Returns:
            List of dicts with port_name, short_name, description, status.
        """
        try:
            with self._connect() as conn:
                output = conn.send_command("sh int description")
                return self._parse_interface_description(output)

        except CiscoSSHError:
            raise
        except Exception as e:
            logger.error(f"Error discovering ports on {self.switch.name}: {e}")
            raise CiscoSSHError(f"Failed to discover ports: {e}") from e

    def _parse_interface_description(self, output: str) -> list[dict[str, Any]]:
        """
        Parse 'sh int description' output for available ports.

        Args:
            output: Raw command output.

        Returns:
            List of available ports with their details.
        """
        available_ports = []
        lines = output.strip().split("\n")

        for line in lines:
            # Skip header line
            if line.startswith("Interface") or not line.strip():
                continue

            # Parse line: Interface, Status, Protocol, Description
            # Format: Gi1/0/7                        admin down     down     Available
            parts = line.split()
            if len(parts) < 3:
                continue

            interface = parts[0]

            # Skip non-physical interfaces (VLANs, etc.)
            if not interface.startswith("Gi") and not interface.startswith("Fa"):
                continue

            # Check for "admin down" status
            status_str = " ".join(parts[1:3]).lower()
            if "admin down" not in status_str:
                continue

            # Get description (everything after protocol status)
            # Find where description starts
            description = ""
            if len(parts) > 3:
                # Rebuild description from remaining parts
                description = " ".join(parts[3:])

            # Only include ports with "Available" description
            if description.strip().lower() != "available":
                continue

            # Convert short name to full name
            port_name = self._expand_port_name(interface)

            available_ports.append({
                "port_name": port_name,
                "short_name": interface,
                "description": description.strip(),
                "status": "available",
            })

        logger.info(f"Discovered {len(available_ports)} available ports on {self.switch.name}")
        return available_ports

    def _expand_port_name(self, short_name: str) -> str:
        """Expand short interface name to full name."""
        if short_name.startswith("Gi"):
            return "GigabitEthernet" + short_name[2:]
        elif short_name.startswith("Fa"):
            return "FastEthernet" + short_name[2:]
        return short_name
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python3 -m pytest tests/test_cisco_ssh_discovery.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/cisco_ssh.py backend/tests/test_cisco_ssh_discovery.py
git commit -m "feat: add port discovery to CiscoSSHService"
```

### Task 2.2: Add Port Verification Method

**Files:**
- Modify: `backend/app/services/cisco_ssh.py`
- Modify: `backend/tests/test_cisco_ssh_discovery.py`

- [ ] **Step 1: Write failing test for verify_port_state**

Add to `backend/tests/test_cisco_ssh_discovery.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_cisco_ssh_discovery.py::TestVerifyPortState -v`
Expected: FAIL

- [ ] **Step 3: Implement verify_port_state method**

Add to `backend/app/services/cisco_ssh.py`:

```python
    def verify_port_state(self, port_number: str) -> dict[str, Any]:
        """
        Verify current state of a port.

        Args:
            port_number: Interface name (e.g., "Gi1/0/7").

        Returns:
            Dict with is_admin_down, is_connected, description.
        """
        try:
            with self._connect() as conn:
                output = conn.send_command(f"sh int {port_number}")
                return self._parse_port_state(output)

        except CiscoSSHError:
            raise
        except Exception as e:
            logger.error(f"Error verifying port {port_number}: {e}")
            raise CiscoSSHError(f"Failed to verify port state: {e}") from e

    def _parse_port_state(self, output: str) -> dict[str, Any]:
        """
        Parse 'sh int <port>' output for state.

        Args:
            output: Raw command output.

        Returns:
            Dict with port state details.
        """
        lines = output.strip().split("\n")
        state = {
            "is_admin_down": False,
            "is_connected": False,
            "description": "",
            "raw_status": "",
        }

        for line in lines:
            line_lower = line.lower()

            # First line has status
            if "is administratively down" in line_lower:
                state["is_admin_down"] = True
                state["raw_status"] = "administratively down"
            elif "is up" in line_lower and "line protocol is up" in line_lower:
                state["is_connected"] = True
                state["raw_status"] = "up"
            elif "is down" in line_lower and "administratively" not in line_lower:
                state["raw_status"] = "down"

            # Description line
            if line.strip().startswith("Description:"):
                state["description"] = line.split(":", 1)[1].strip()

        return state
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python3 -m pytest tests/test_cisco_ssh_discovery.py::TestVerifyPortState -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/cisco_ssh.py backend/tests/test_cisco_ssh_discovery.py
git commit -m "feat: add port state verification to CiscoSSHService"
```

### Task 2.3: Add Port Assignment Commands

**Files:**
- Modify: `backend/app/services/cisco_ssh.py`
- Modify: `backend/tests/test_cisco_ssh_discovery.py`

- [ ] **Step 1: Write failing test for configure_port**

Add to `backend/tests/test_cisco_ssh_discovery.py`:

```python
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
        assert "no shutdown" in commands

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_cisco_ssh_discovery.py::TestConfigurePort -v`
Expected: FAIL

- [ ] **Step 3: Implement configure_port_assign and configure_port_release**

Add to `backend/app/services/cisco_ssh.py`:

```python
    def configure_port_assign(
        self, port_number: str, simulator_name: str, vlan: int
    ) -> bool:
        """
        Configure port for simulator assignment.

        Args:
            port_number: Interface name (e.g., "Gi1/0/7").
            simulator_name: Name to use in description.
            vlan: VLAN ID to assign.

        Returns:
            True if successful.
        """
        commands = [
            f"interface {port_number}",
            f"description SIMPORT:{simulator_name}",
            "switchport",
            "switchport mode access",
            f"switchport access vlan {vlan}",
            "no shutdown",
        ]

        try:
            with self._connect() as conn:
                logger.info(
                    f"Configuring port {port_number} for {simulator_name} on VLAN {vlan}"
                )
                output = conn.send_config_set(commands)
                logger.debug(f"Config output: {output}")

                # Write config
                conn.send_command("wr mem")
                logger.info(f"Port {port_number} configured and saved")
                return True

        except CiscoSSHError:
            raise
        except Exception as e:
            logger.error(f"Error configuring port {port_number}: {e}")
            raise CiscoSSHError(f"Failed to configure port: {e}") from e

    def configure_port_release(self, port_number: str, vlan: int) -> bool:
        """
        Release port back to Available state.

        Args:
            port_number: Interface name (e.g., "Gi1/0/7").
            vlan: Current VLAN to remove.

        Returns:
            True if successful.
        """
        commands = [
            f"interface {port_number}",
            "description Available",
            f"no switchport access vlan {vlan}",
            "shutdown",
        ]

        try:
            with self._connect() as conn:
                logger.info(f"Releasing port {port_number} back to Available")
                output = conn.send_config_set(commands)
                logger.debug(f"Config output: {output}")

                # Write config
                conn.send_command("wr mem")
                logger.info(f"Port {port_number} released and saved")
                return True

        except CiscoSSHError:
            raise
        except Exception as e:
            logger.error(f"Error releasing port {port_number}: {e}")
            raise CiscoSSHError(f"Failed to release port: {e}") from e
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python3 -m pytest tests/test_cisco_ssh_discovery.py::TestConfigurePort -v`
Expected: PASS

- [ ] **Step 5: Add async wrappers**

Add async versions after the sync methods:

```python
    async def discover_ports_async(self) -> list[dict[str, Any]]:
        """Async wrapper for discover_ports."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_ssh_executor, self.discover_ports)

    async def verify_port_state_async(self, port_number: str) -> dict[str, Any]:
        """Async wrapper for verify_port_state."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _ssh_executor, self.verify_port_state, port_number
        )

    async def configure_port_assign_async(
        self, port_number: str, simulator_name: str, vlan: int
    ) -> bool:
        """Async wrapper for configure_port_assign."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _ssh_executor, self.configure_port_assign, port_number, simulator_name, vlan
        )

    async def configure_port_release_async(self, port_number: str, vlan: int) -> bool:
        """Async wrapper for configure_port_release."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _ssh_executor, self.configure_port_release, port_number, vlan
        )
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/cisco_ssh.py backend/tests/test_cisco_ssh_discovery.py
git commit -m "feat: add port assignment and release commands"
```

---

## Chunk 3: Port Discovery Service

### Task 3.1: Create Discovery Schemas

**Files:**
- Create: `backend/app/schemas/discovery.py`

- [ ] **Step 1: Create schemas file**

```python
# backend/app/schemas/discovery.py
"""Schemas for port discovery endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class DiscoveredPortOut(BaseModel):
    """Schema for discovered port response."""

    id: int
    switch_id: int
    switch_name: str
    port_name: str
    short_name: str
    status: str
    description: str | None
    discovered_at: datetime
    last_verified_at: datetime | None
    error_message: str | None
    assigned_simulator_name: str | None = None

    class Config:
        from_attributes = True


class DiscoveredPortListOut(BaseModel):
    """Schema for list of discovered ports."""

    ports: list[DiscoveredPortOut]
    total: int
    available_count: int
    assigned_count: int
    error_count: int


class ScanResult(BaseModel):
    """Result of a port scan operation."""

    success: bool
    message: str
    ports_found: int
    new_ports: int
    removed_ports: int


class PortAssignRequest(BaseModel):
    """Request to assign a discovered port to a simulator."""

    discovered_port_id: int
    simulator_id: int
    vlan: int = Field(default=30, ge=1, le=4094)
    timeout_hours: int = Field(default=4, ge=1, le=24)


class PortAssignResult(BaseModel):
    """Result of a port assignment."""

    success: bool
    message: str
    port_id: int | None = None
    error: str | None = None


class PortReleaseResult(BaseModel):
    """Result of releasing a port."""

    success: bool
    message: str
    error: str | None = None
```

- [ ] **Step 2: Verify syntax**

Run: `python3 -m py_compile backend/app/schemas/discovery.py`
Expected: No output (success)

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/discovery.py
git commit -m "feat: add discovery schemas"
```

### Task 3.2: Create Port Discovery Service

**Files:**
- Create: `backend/app/services/port_discovery.py`
- Create: `backend/tests/test_port_discovery_service.py`

- [ ] **Step 1: Write failing test for scan_switch**

Create `backend/tests/test_port_discovery_service.py`:

```python
"""Tests for PortDiscoveryService."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.discovered_port import DiscoveredPort
from app.models.switch import Switch
from app.services.port_discovery import PortDiscoveryService


@pytest.mark.asyncio
class TestScanSwitch:
    """Tests for switch scanning."""

    async def test_scan_creates_discovered_ports(self, db_session):
        """Should create DiscoveredPort records for available ports."""
        # Create test switch
        switch = Switch(
            name="TestSwitch",
            ip_address="192.168.1.1",
            username="admin",
            password_encrypted="encrypted",
        )
        db_session.add(switch)
        await db_session.commit()
        await db_session.refresh(switch)

        mock_ports = [
            {"port_name": "GigabitEthernet1/0/7", "short_name": "Gi1/0/7", "description": "Available", "status": "available"},
            {"port_name": "GigabitEthernet1/0/8", "short_name": "Gi1/0/8", "description": "Available", "status": "available"},
        ]

        with patch("app.services.port_discovery.CiscoSSHService") as mock_ssh:
            mock_instance = MagicMock()
            mock_instance.discover_ports_async = AsyncMock(return_value=mock_ports)
            mock_ssh.return_value = mock_instance

            service = PortDiscoveryService(db_session)
            result = await service.scan_switch(switch.id)

        assert result["success"] is True
        assert result["ports_found"] == 2
        assert result["new_ports"] == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_port_discovery_service.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.services.port_discovery'"

- [ ] **Step 3: Implement PortDiscoveryService**

Create `backend/app/services/port_discovery.py`:

```python
# backend/app/services/port_discovery.py
"""
Port discovery service for scanning switches and managing discovered ports.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.activity_log import ActivityLog
from app.models.discovered_port import DiscoveredPort
from app.models.port_assignment import PortAssignment
from app.models.simulator import Simulator
from app.models.switch import Switch
from app.services.cisco_ssh import CiscoSSHError, CiscoSSHService

logger = logging.getLogger(__name__)


class PortDiscoveryError(Exception):
    """Exception for port discovery operations."""

    pass


class PortDiscoveryService:
    """Service for discovering and managing switch ports."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize service with database session."""
        self.db = db

    async def get_switch(self, switch_id: int) -> Switch | None:
        """Get switch by ID with discovered ports."""
        result = await self.db.execute(
            select(Switch)
            .where(Switch.id == switch_id)
            .options(selectinload(Switch.discovered_ports))
        )
        return result.scalar_one_or_none()

    async def scan_switch(self, switch_id: int) -> dict:
        """
        Scan a switch for available ports.

        Args:
            switch_id: ID of the switch to scan.

        Returns:
            Dict with scan results.
        """
        switch = await self.get_switch(switch_id)
        if not switch:
            return {"success": False, "message": "Switch not found", "ports_found": 0, "new_ports": 0, "removed_ports": 0}

        try:
            ssh_service = CiscoSSHService(switch)
            discovered = await ssh_service.discover_ports_async()
        except CiscoSSHError as e:
            logger.error(f"SSH error scanning switch {switch.name}: {e}")
            return {"success": False, "message": str(e), "ports_found": 0, "new_ports": 0, "removed_ports": 0}

        # Get existing discovered ports for this switch
        existing_ports = {p.short_name: p for p in switch.discovered_ports}
        discovered_names = {p["short_name"] for p in discovered}

        new_count = 0
        removed_count = 0

        # Add new ports
        for port_data in discovered:
            if port_data["short_name"] not in existing_ports:
                new_port = DiscoveredPort(
                    switch_id=switch_id,
                    port_name=port_data["port_name"],
                    short_name=port_data["short_name"],
                    description=port_data["description"],
                    status="available",
                    discovered_at=datetime.now(UTC),
                    last_verified_at=datetime.now(UTC),
                )
                self.db.add(new_port)
                new_count += 1
                logger.info(f"Discovered new port: {port_data['short_name']} on {switch.name}")
            else:
                # Update existing port
                existing = existing_ports[port_data["short_name"]]
                if existing.status == "available":
                    existing.description = port_data["description"]
                    existing.last_verified_at = datetime.now(UTC)

        # Mark ports that disappeared as error (if they were available)
        for short_name, port in existing_ports.items():
            if short_name not in discovered_names and port.status == "available":
                port.status = "error"
                port.error_message = "Port not found during scan"
                removed_count += 1
                logger.warning(f"Port {short_name} not found on {switch.name}")

        await self.db.commit()

        return {
            "success": True,
            "message": f"Scan complete. Found {len(discovered)} available ports.",
            "ports_found": len(discovered),
            "new_ports": new_count,
            "removed_ports": removed_count,
        }

    async def get_discovered_ports(
        self, switch_id: int | None = None, status: str | None = None
    ) -> list[DiscoveredPort]:
        """Get discovered ports, optionally filtered."""
        query = select(DiscoveredPort).options(
            selectinload(DiscoveredPort.switch),
            selectinload(DiscoveredPort.port_assignment).selectinload(PortAssignment.simulator),
        )

        if switch_id:
            query = query.where(DiscoveredPort.switch_id == switch_id)
        if status:
            query = query.where(DiscoveredPort.status == status)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def assign_port(
        self,
        discovered_port_id: int,
        simulator_id: int,
        vlan: int,
        timeout_hours: int,
        user_id: int,
    ) -> dict:
        """
        Assign a discovered port to a simulator.

        Args:
            discovered_port_id: ID of the discovered port.
            simulator_id: ID of the simulator to assign to.
            vlan: VLAN ID.
            timeout_hours: Default timeout in hours.
            user_id: ID of user performing the action.

        Returns:
            Dict with assignment result.
        """
        # Get discovered port
        result = await self.db.execute(
            select(DiscoveredPort)
            .where(DiscoveredPort.id == discovered_port_id)
            .options(selectinload(DiscoveredPort.switch))
        )
        discovered_port = result.scalar_one_or_none()

        if not discovered_port:
            return {"success": False, "message": "Port not found", "port_id": None}

        if discovered_port.status != "available":
            return {"success": False, "message": f"Port is not available (status: {discovered_port.status})", "port_id": None}

        # Get simulator
        result = await self.db.execute(
            select(Simulator).where(Simulator.id == simulator_id)
        )
        simulator = result.scalar_one_or_none()

        if not simulator:
            return {"success": False, "message": "Simulator not found", "port_id": None}

        # Configure port on switch
        try:
            ssh_service = CiscoSSHService(discovered_port.switch)
            await ssh_service.configure_port_assign_async(
                discovered_port.short_name, simulator.short_name, vlan
            )
        except CiscoSSHError as e:
            logger.error(f"Failed to configure port: {e}")
            return {"success": False, "message": f"SSH error: {e}", "port_id": None}

        # Verify configuration
        try:
            state = await ssh_service.verify_port_state_async(discovered_port.short_name)
            expected_desc = f"SIMPORT:{simulator.short_name}"

            if state["is_admin_down"]:
                discovered_port.status = "error"
                discovered_port.error_message = "Port still admin down after enable"
                await self.db.commit()
                return {"success": False, "message": "Verification failed: port still disabled", "port_id": None}

            if state["description"] != expected_desc:
                logger.warning(f"Description mismatch: expected '{expected_desc}', got '{state['description']}'")
        except CiscoSSHError as e:
            logger.error(f"Verification failed: {e}")
            discovered_port.status = "error"
            discovered_port.error_message = f"Verification failed: {e}"
            await self.db.commit()
            return {"success": False, "message": f"Verification failed: {e}", "port_id": None}

        # Create port assignment
        port_assignment = PortAssignment(
            simulator_id=simulator_id,
            switch_id=discovered_port.switch_id,
            discovered_port_id=discovered_port_id,
            port_number=discovered_port.short_name,
            vlan=vlan,
            timeout_hours=timeout_hours,
            status="enabled",
            enabled_at=datetime.now(UTC),
        )
        self.db.add(port_assignment)

        # Update discovered port status
        discovered_port.status = "assigned"
        discovered_port.last_verified_at = datetime.now(UTC)
        discovered_port.error_message = None

        # Log activity
        log_entry = ActivityLog(
            user_id=user_id,
            simulator_id=simulator_id,
            action="port_assigned",
            vlan=vlan,
            details={
                "port": discovered_port.short_name,
                "switch": discovered_port.switch.name,
            },
        )
        self.db.add(log_entry)

        await self.db.commit()
        await self.db.refresh(port_assignment)

        logger.info(f"Assigned port {discovered_port.short_name} to {simulator.name}")
        return {"success": True, "message": f"Port assigned to {simulator.name}", "port_id": port_assignment.id}

    async def release_port(self, port_assignment_id: int, user_id: int | None = None) -> dict:
        """
        Release a port back to available.

        Args:
            port_assignment_id: ID of the port assignment to release.
            user_id: ID of user performing the action.

        Returns:
            Dict with release result.
        """
        # Get port assignment with related data
        result = await self.db.execute(
            select(PortAssignment)
            .where(PortAssignment.id == port_assignment_id)
            .options(
                selectinload(PortAssignment.switch),
                selectinload(PortAssignment.simulator),
                selectinload(PortAssignment.discovered_port),
            )
        )
        assignment = result.scalar_one_or_none()

        if not assignment:
            return {"success": False, "message": "Port assignment not found"}

        # Release port on switch
        try:
            ssh_service = CiscoSSHService(assignment.switch)
            await ssh_service.configure_port_release_async(
                assignment.port_number, assignment.vlan
            )
        except CiscoSSHError as e:
            logger.error(f"Failed to release port: {e}")
            return {"success": False, "message": f"SSH error: {e}"}

        # Verify release
        try:
            state = await ssh_service.verify_port_state_async(assignment.port_number)

            if not state["is_admin_down"]:
                if assignment.discovered_port:
                    assignment.discovered_port.status = "error"
                    assignment.discovered_port.error_message = "Port not admin down after release"
                await self.db.commit()
                return {"success": False, "message": "Verification failed: port not disabled"}

            if state["description"] != "Available":
                logger.warning(f"Description not reset: {state['description']}")
        except CiscoSSHError as e:
            logger.error(f"Verification failed: {e}")
            if assignment.discovered_port:
                assignment.discovered_port.status = "error"
                assignment.discovered_port.error_message = f"Verification failed: {e}"
            await self.db.commit()
            return {"success": False, "message": f"Verification failed: {e}"}

        # Update discovered port
        if assignment.discovered_port:
            assignment.discovered_port.status = "available"
            assignment.discovered_port.last_verified_at = datetime.now(UTC)
            assignment.discovered_port.error_message = None

        # Log activity
        log_entry = ActivityLog(
            user_id=user_id,
            simulator_id=assignment.simulator_id,
            action="port_released",
            vlan=assignment.vlan,
            details={
                "port": assignment.port_number,
                "switch": assignment.switch.name,
            },
        )
        self.db.add(log_entry)

        # Delete assignment
        await self.db.delete(assignment)
        await self.db.commit()

        logger.info(f"Released port {assignment.port_number}")
        return {"success": True, "message": "Port released to available"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python3 -m pytest tests/test_port_discovery_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/port_discovery.py backend/tests/test_port_discovery_service.py
git commit -m "feat: add PortDiscoveryService"
```

---

## Chunk 4: API Endpoints

### Task 4.1: Create Discovery Router

**Files:**
- Create: `backend/app/routers/discovery.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create discovery router**

```python
# backend/app/routers/discovery.py
"""
Port discovery API endpoints.
"""

import logging

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.dependencies import AdminUser, CurrentUser, DbSession
from app.models.discovered_port import DiscoveredPort
from app.models.switch import Switch
from app.schemas.discovery import (
    DiscoveredPortListOut,
    DiscoveredPortOut,
    PortAssignRequest,
    PortAssignResult,
    PortReleaseResult,
    ScanResult,
)
from app.services.port_discovery import PortDiscoveryService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/discovery", tags=["Discovery"])


def _port_to_out(port: DiscoveredPort) -> DiscoveredPortOut:
    """Convert DiscoveredPort model to schema."""
    assigned_sim = None
    if port.port_assignment and port.port_assignment.simulator:
        assigned_sim = port.port_assignment.simulator.name

    return DiscoveredPortOut(
        id=port.id,
        switch_id=port.switch_id,
        switch_name=port.switch.name,
        port_name=port.port_name,
        short_name=port.short_name,
        status=port.status,
        description=port.description,
        discovered_at=port.discovered_at,
        last_verified_at=port.last_verified_at,
        error_message=port.error_message,
        assigned_simulator_name=assigned_sim,
    )


@router.post("/switches/{switch_id}/scan", response_model=ScanResult)
async def scan_switch(
    switch_id: int, db: DbSession, admin: AdminUser
) -> ScanResult:
    """Scan a switch for available ports (admin only)."""
    service = PortDiscoveryService(db)
    result = await service.scan_switch(switch_id)

    return ScanResult(
        success=result["success"],
        message=result["message"],
        ports_found=result["ports_found"],
        new_ports=result["new_ports"],
        removed_ports=result["removed_ports"],
    )


@router.get("/switches/{switch_id}/ports", response_model=DiscoveredPortListOut)
async def list_switch_ports(
    switch_id: int, db: DbSession, admin: AdminUser
) -> DiscoveredPortListOut:
    """List discovered ports for a switch (admin only)."""
    service = PortDiscoveryService(db)
    ports = await service.get_discovered_ports(switch_id=switch_id)

    available = sum(1 for p in ports if p.status == "available")
    assigned = sum(1 for p in ports if p.status == "assigned")
    errors = sum(1 for p in ports if p.status == "error")

    return DiscoveredPortListOut(
        ports=[_port_to_out(p) for p in ports],
        total=len(ports),
        available_count=available,
        assigned_count=assigned,
        error_count=errors,
    )


@router.get("/ports", response_model=DiscoveredPortListOut)
async def list_all_discovered_ports(
    db: DbSession, admin: AdminUser, status: str | None = None
) -> DiscoveredPortListOut:
    """List all discovered ports (admin only)."""
    service = PortDiscoveryService(db)
    ports = await service.get_discovered_ports(status=status)

    available = sum(1 for p in ports if p.status == "available")
    assigned = sum(1 for p in ports if p.status == "assigned")
    errors = sum(1 for p in ports if p.status == "error")

    return DiscoveredPortListOut(
        ports=[_port_to_out(p) for p in ports],
        total=len(ports),
        available_count=available,
        assigned_count=assigned,
        error_count=errors,
    )


@router.post("/ports/assign", response_model=PortAssignResult)
async def assign_port(
    request: PortAssignRequest, db: DbSession, admin: AdminUser
) -> PortAssignResult:
    """Assign a discovered port to a simulator (admin only)."""
    service = PortDiscoveryService(db)
    result = await service.assign_port(
        discovered_port_id=request.discovered_port_id,
        simulator_id=request.simulator_id,
        vlan=request.vlan,
        timeout_hours=request.timeout_hours,
        user_id=admin.id,
    )

    return PortAssignResult(
        success=result["success"],
        message=result["message"],
        port_id=result.get("port_id"),
        error=result.get("error"),
    )


@router.delete("/ports/assignments/{assignment_id}", response_model=PortReleaseResult)
async def release_port(
    assignment_id: int, db: DbSession, admin: AdminUser
) -> PortReleaseResult:
    """Release a port back to available (admin only)."""
    service = PortDiscoveryService(db)
    result = await service.release_port(assignment_id, admin.id)

    return PortReleaseResult(
        success=result["success"],
        message=result["message"],
        error=result.get("error"),
    )


@router.post("/ports/{port_id}/refresh", response_model=DiscoveredPortOut)
async def refresh_port_status(
    port_id: int, db: DbSession, admin: AdminUser
) -> DiscoveredPortOut:
    """Refresh status of a single discovered port (admin only)."""
    result = await db.execute(
        select(DiscoveredPort)
        .where(DiscoveredPort.id == port_id)
        .options(
            selectinload(DiscoveredPort.switch),
            selectinload(DiscoveredPort.port_assignment),
        )
    )
    port = result.scalar_one_or_none()

    if not port:
        raise HTTPException(status_code=404, detail="Port not found")

    # TODO: Implement single port refresh with verification
    # For now, just return current state

    return _port_to_out(port)
```

- [ ] **Step 2: Add router to main.py**

Add import to `backend/app/main.py`:
```python
from app.routers import auth, discovery, logs, ports, simulators, switches, system, users
```

Add router inclusion after other routers:
```python
app.include_router(discovery.router, prefix="/api")
```

- [ ] **Step 3: Verify syntax**

Run: `python3 -m py_compile backend/app/routers/discovery.py`
Expected: No output (success)

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/discovery.py backend/app/main.py
git commit -m "feat: add discovery API endpoints"
```

### Task 4.2: Update Switches Router to Auto-Scan

**Files:**
- Modify: `backend/app/routers/switches.py`

- [ ] **Step 1: Add auto-scan on switch creation**

Add import at top of `backend/app/routers/switches.py`:
```python
from app.services.port_discovery import PortDiscoveryService
```

Modify `create_switch` function to trigger scan after creation:
```python
@router.post("", response_model=SwitchOut, status_code=status.HTTP_201_CREATED)
async def create_switch(
    data: SwitchCreate, db: DbSession, admin: AdminUser
) -> SwitchOut:
    """Create a new switch (admin only)."""
    encryption = get_encryption_service()

    switch = Switch(
        name=data.name,
        ip_address=data.ip_address,
        username=data.username,
        password_encrypted=encryption.encrypt(data.password),
        device_type=data.device_type,
    )
    db.add(switch)
    await db.commit()
    await db.refresh(switch)

    logger.info(f"Created switch '{switch.name}' ({switch.ip_address})")

    # Auto-scan for available ports
    try:
        discovery_service = PortDiscoveryService(db)
        scan_result = await discovery_service.scan_switch(switch.id)
        logger.info(f"Auto-scan result: {scan_result['message']}")
    except Exception as e:
        logger.warning(f"Auto-scan failed for new switch: {e}")

    return SwitchOut.model_validate(switch)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/routers/switches.py
git commit -m "feat: auto-scan ports when switch is added"
```

---

## Chunk 5: Frontend Updates

### Task 5.1: Create PortLegend Component

**Files:**
- Create: `frontend/src/components/PortLegend.vue`

- [ ] **Step 1: Create legend component**

```vue
<!-- frontend/src/components/PortLegend.vue -->
<script setup>
// No props needed - static legend
</script>

<template>
  <div class="port-legend flex items-center justify-center gap-6 py-3 px-4 bg-gray-100 dark:bg-gray-800 rounded-lg text-sm">
    <div class="flex items-center gap-2">
      <span class="w-3 h-3 rounded-full bg-red-500"></span>
      <span class="text-secondary">In Use</span>
    </div>
    <div class="flex items-center gap-2">
      <span class="w-3 h-3 rounded-full bg-gray-400"></span>
      <span class="text-secondary">Available</span>
    </div>
    <div class="flex items-center gap-2">
      <span class="w-3 h-3 rounded-full bg-blue-500"></span>
      <span class="text-secondary">Assigned/Off</span>
    </div>
    <div class="flex items-center gap-2">
      <span class="w-3 h-3 rounded-full bg-emerald-500"></span>
      <span class="text-secondary">Active (timer)</span>
    </div>
    <div class="flex items-center gap-2">
      <span class="w-3 h-3 rounded-full bg-yellow-500"></span>
      <span class="text-secondary">Error</span>
    </div>
  </div>
</template>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/PortLegend.vue
git commit -m "feat: add PortLegend component"
```

### Task 5.2: Create PortStatusBadge Component

**Files:**
- Create: `frontend/src/components/PortStatusBadge.vue`

- [ ] **Step 1: Create status badge component**

```vue
<!-- frontend/src/components/PortStatusBadge.vue -->
<script setup>
import { computed } from 'vue'
import { SignalIcon, SignalSlashIcon, ExclamationTriangleIcon } from '@heroicons/vue/24/outline'

const props = defineProps({
  status: {
    type: String,
    required: true,
    validator: (v) => ['in_use', 'available', 'assigned', 'enabled', 'error'].includes(v)
  },
  secondsRemaining: {
    type: Number,
    default: null
  }
})

const colorClasses = computed(() => {
  switch (props.status) {
    case 'in_use':
      return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
    case 'available':
      return 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
    case 'assigned':
      return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
    case 'enabled':
      return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
    case 'error':
      return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
    default:
      return 'bg-gray-100 text-gray-700'
  }
})

const iconColorClasses = computed(() => {
  switch (props.status) {
    case 'in_use':
      return 'text-red-500'
    case 'available':
      return 'text-gray-400'
    case 'assigned':
      return 'text-blue-500'
    case 'enabled':
      return 'text-emerald-500'
    case 'error':
      return 'text-yellow-500'
    default:
      return 'text-gray-400'
  }
})

function formatTime(seconds) {
  if (!seconds || seconds <= 0) return ''
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  if (hours > 0) return `${hours}h ${minutes}m`
  return `${minutes}m`
}
</script>

<template>
  <div
    class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium"
    :class="colorClasses"
  >
    <ExclamationTriangleIcon v-if="status === 'error'" class="h-4 w-4" :class="iconColorClasses" />
    <SignalSlashIcon v-else-if="status === 'assigned' || status === 'in_use'" class="h-4 w-4" :class="iconColorClasses" />
    <SignalIcon v-else class="h-4 w-4" :class="iconColorClasses" />

    <span v-if="status === 'enabled' && secondsRemaining">
      {{ formatTime(secondsRemaining) }}
    </span>
    <span v-else>
      {{ status === 'in_use' ? 'In Use' : status.charAt(0).toUpperCase() + status.slice(1) }}
    </span>
  </div>
</template>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/PortStatusBadge.vue
git commit -m "feat: add PortStatusBadge component"
```

### Task 5.3: Add Discovery API Methods

**Files:**
- Modify: `frontend/src/services/api.js`

- [ ] **Step 1: Add discovery API methods**

Add to `frontend/src/services/api.js`:

```javascript
export const discoveryApi = {
  scanSwitch: (switchId) => api.post(`/discovery/switches/${switchId}/scan`),
  getSwitchPorts: (switchId) => api.get(`/discovery/switches/${switchId}/ports`),
  getAllPorts: (status = null) => api.get('/discovery/ports', { params: { status } }),
  assignPort: (data) => api.post('/discovery/ports/assign', data),
  releasePort: (assignmentId) => api.delete(`/discovery/ports/assignments/${assignmentId}`),
  refreshPort: (portId) => api.post(`/discovery/ports/${portId}/refresh`),
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/services/api.js
git commit -m "feat: add discovery API methods"
```

### Task 5.4: Update SimulatorDetailView Colors

**Files:**
- Modify: `frontend/src/views/SimulatorDetailView.vue`

- [ ] **Step 1: Update port colors and add legend**

Import the legend component:
```javascript
import PortLegend from '@/components/PortLegend.vue'
```

Update the port icon classes to use new colors:
```vue
<!-- Replace the existing port icon div -->
<div
  class="w-16 h-16 rounded-lg flex items-center justify-center"
  :class="{
    'bg-emerald-100 dark:bg-emerald-900/30': port.status === 'enabled',
    'bg-blue-100 dark:bg-blue-900/30': port.status === 'disabled',
    'bg-yellow-100 dark:bg-yellow-900/30': port.status === 'error'
  }"
>
  <SignalIcon
    class="h-8 w-8"
    :class="{
      'text-emerald-500': port.status === 'enabled',
      'text-blue-500': port.status === 'disabled',
      'text-yellow-500': port.status === 'error'
    }"
  />
</div>
```

Update button colors:
```vue
<button
  @click="openConfirmModal(port, port.status === 'enabled' ? 'disable' : 'enable')"
  :disabled="loading"
  class="btn"
  :class="port.status === 'enabled' ? 'btn-blue' : 'btn-success'"
>
  {{ port.status === 'enabled' ? 'Disable' : 'Enable' }}
</button>
```

Add legend at bottom of main content:
```vue
<!-- After the ports list, before closing </main> -->
<PortLegend class="mt-8" />
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/SimulatorDetailView.vue
git commit -m "feat: update port colors and add legend"
```

### Task 5.5: Support Multiple Ports Per Simulator

**Files:**
- Modify: `frontend/src/views/SimulatorDetailView.vue`

Simulators can have multiple ports assigned (e.g., CL350 with Gi1/0/7 and Gi1/0/8). Update the UI to:
- Display all assigned ports as a list of badges
- Each port badge shows name, status, and timer independently
- Add "Add Port" button to assign additional ports from available pool
- Each port can be enabled/disabled independently

- [ ] **Step 1: Update port list display**

Replace the single port card with a list that iterates through all ports:
```vue
<!-- Replace single port display with multi-port list -->
<div class="space-y-4">
  <div v-for="port in simulator.port_assignments" :key="port.id" class="flex items-center justify-between p-4 bg-white dark:bg-gray-800 rounded-lg shadow">
    <!-- Port info -->
    <div class="flex items-center gap-4">
      <div
        class="w-12 h-12 rounded-lg flex items-center justify-center"
        :class="{
          'bg-emerald-100 dark:bg-emerald-900/30': port.status === 'enabled',
          'bg-blue-100 dark:bg-blue-900/30': port.status === 'disabled',
          'bg-yellow-100 dark:bg-yellow-900/30': port.status === 'error'
        }"
      >
        <SignalIcon
          class="h-6 w-6"
          :class="{
            'text-emerald-500': port.status === 'enabled',
            'text-blue-500': port.status === 'disabled',
            'text-yellow-500': port.status === 'error'
          }"
        />
      </div>
      <div>
        <p class="font-medium">{{ port.port_number }}</p>
        <p class="text-sm text-gray-500">VLAN {{ port.vlan }}</p>
      </div>
    </div>

    <!-- Status and timer -->
    <div class="flex items-center gap-4">
      <div v-if="port.status === 'enabled' && getSecondsRemaining(port) > 0" class="text-sm text-emerald-600 dark:text-emerald-400 font-mono">
        {{ formatTimeRemaining(getSecondsRemaining(port)) }}
      </div>
      <button
        @click="openConfirmModal(port, port.status === 'enabled' ? 'disable' : 'enable')"
        :disabled="loading"
        class="btn"
        :class="port.status === 'enabled' ? 'btn-blue' : 'btn-success'"
      >
        {{ port.status === 'enabled' ? 'Disable' : 'Enable' }}
      </button>
    </div>
  </div>
</div>

<!-- Add Port button for admins -->
<button
  v-if="isAdmin"
  @click="showAddPortModal = true"
  class="mt-4 btn btn-outline flex items-center gap-2"
>
  <PlusIcon class="h-5 w-5" />
  Add Port
</button>
```

- [ ] **Step 2: Add AddPortModal component reference**

Import and add modal for selecting available ports:
```javascript
import { PlusIcon } from '@heroicons/vue/24/outline'

const showAddPortModal = ref(false)
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/SimulatorDetailView.vue
git commit -m "feat: support multiple ports per simulator"
```

---

## Final Steps

### Task 6.1: Run All Tests

- [ ] **Step 1: Run backend tests**

```bash
cd backend && python3 -m pytest -v
```
Expected: All tests pass

- [ ] **Step 2: Run linter**

```bash
cd backend && python3 -m ruff check .
```
Expected: No errors

- [ ] **Step 3: Commit any fixes**

If there are lint issues, fix them and commit.

### Task 6.2: Final Commit

- [ ] **Step 1: Create final commit**

```bash
git add -A
git commit -m "feat: complete port discovery implementation"
```

- [ ] **Step 2: Push changes**

```bash
git push
```
