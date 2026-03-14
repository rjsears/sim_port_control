# Port Discovery & Safe Assignment Design

**Date:** 2026-03-10
**Status:** Approved

## Overview

Add automatic port discovery to prevent accidental misconfiguration of switch ports. Only ports explicitly marked as "Available" and administratively down can be assigned to simulators. All port operations are verified after execution.

## Problem

Currently, admins manually type port names (e.g., "Gi1/0/7") when assigning ports to simulators. This risks:
- Typos causing configuration of wrong ports
- Accidentally reconfiguring ports already in use for production traffic
- No visibility into what ports are actually available

## Solution

Scan switches to discover available ports, track them in the database, and only allow assignment of discovered available ports.

## Cisco IOS Commands

### Discovery
```
sh int description
```
Output identifies available ports by:
- Status: `admin down`
- Description: `Available`

### Port States (from `sh int <port>`)
| Output | Meaning |
|--------|---------|
| `is administratively down` | Port is shut (disabled) |
| `is down` (no "administratively") | Port enabled, no link |
| `is up` | Port enabled, connected |

### Operations

**Assign (take ownership):**
```
conf t
interface GigabitEthernet1/0/X
description SIMPORT:<simulator_name>
switchport
switchport mode access
switchport access vlan <vlan>
no shutdown
end
wr mem
```

**Enable:**
```
conf t
interface GigabitEthernet1/0/X
no shutdown
end
wr mem
```

**Disable:**
```
conf t
interface GigabitEthernet1/0/X
shutdown
end
wr mem
```

**Delete (release back to available):**
```
conf t
interface GigabitEthernet1/0/X
description Available
no switchport access vlan <vlan>
shutdown
end
wr mem
```

## Database Model

### New Table: `discovered_ports`

| Column | Type | Description |
|--------|------|-------------|
| `id` | int | Primary key |
| `switch_id` | FK → switches | Which switch this port is on |
| `port_name` | str | e.g., "GigabitEthernet1/0/7" |
| `short_name` | str | e.g., "Gi1/0/7" (for display) |
| `status` | enum | `available`, `assigned`, `error` |
| `description` | str | Current description from switch |
| `discovered_at` | datetime | When first discovered |
| `last_verified_at` | datetime | Last successful verification |
| `assigned_to_port_id` | FK → port_assignments | Link when assigned (nullable) |

### Changes to `port_assignments`
- Add `discovered_port_id` FK → discovered_ports (required)
- Remove free-text `port_number` (get from discovered_port relation)

## Verification

Every operation verifies state after execution using `sh int <port>`:

| Operation | Expected State |
|-----------|----------------|
| Assign | No "administratively", description = "SIMPORT:xxx" |
| Enable | No "administratively" in status |
| Disable | Contains "administratively down" |
| Delete | "administratively down", description = "Available" |

If verification fails:
- Port marked as `error` status
- Details logged to activity_log
- Admin sees yellow error indicator
- Admin can retry operation

## UI Color Scheme

| Color | Status | Click Action |
|-------|--------|--------------|
| Red | In use (not managed by us) | None - view only |
| Gray | Available, not assigned | Admin can assign to simulator |
| Blue | Assigned, disabled (shut) | Toast: "Enable for X hours?" (max 24h) |
| Green | Assigned, enabled | Shows countdown + Toast: "Disable?" |
| Yellow | Error | Shows error details, retry option |

### Footer Legend
```
🔴 In Use    🩶 Available    🔵 Assigned/Off    🟢 Active (timer)    🟡 Error
```

## Service Layer

### PortDiscoveryService

| Method | Description |
|--------|-------------|
| `scan_switch(switch_id)` | Run `sh int description`, parse, update DB |
| `assign_port(discovered_port_id, simulator_id, vlan, timeout)` | Full config + verify |
| `release_port(port_assignment_id)` | Reset to Available + verify |
| `refresh_port_status(discovered_port_id)` | Re-verify single port |

### CiscoSSHService Additions

| Method | Description |
|--------|-------------|
| `discover_ports()` | Run `sh int description`, return parsed list |
| `assign_port(port, sim_name, vlan)` | Full config sequence |
| `release_port(port, vlan)` | Reset to Available |
| `verify_port_state(port)` | Return current state from switch |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/switches/{id}/scan` | POST | Trigger port scan |
| `/api/switches/{id}/ports` | GET | List discovered ports |
| `/api/ports/assign` | POST | Assign discovered port to simulator |
| `/api/ports/assignments/{id}` | DELETE | Release port back to available |

## Activity Log Events

- `port_discovered` - New port found during scan
- `port_assigned` - Port configured for simulator
- `port_released` - Port reset to Available
- `port_error` - Verification failed
- `port_recovered` - Error cleared after retry

## Scan Triggers

1. **On switch add** - Auto-scan when switch is first added
2. **On port management** - Re-scan when entering port config screens
3. **Manual refresh** - Admin clicks "Rescan Ports" button

## Files to Create

- `backend/app/models/discovered_port.py`
- `backend/app/services/port_discovery.py`
- `backend/app/routers/discovery.py`
- `backend/app/schemas/discovery.py`
- `frontend/src/views/admin/DiscoveredPortsView.vue`
- `frontend/src/components/PortLegend.vue`

## Files to Modify

- `backend/app/services/cisco_ssh.py` - Add discover/verify methods
- `backend/app/models/port_assignment.py` - Add discovered_port_id FK
- `backend/app/routers/switches.py` - Trigger scan on switch add
- `backend/app/routers/ports.py` - Use discovered ports for assignment
- `frontend/src/views/SimulatorDetailView.vue` - Updated colors/interactions
- `frontend/src/views/admin/PortsView.vue` - Dropdown instead of text input

## Migration

- Add `discovered_ports` table
- Add `discovered_port_id` to `port_assignments`
- Migrate any existing port assignments
