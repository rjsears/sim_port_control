# SimPortControl Architecture

This document describes the technical architecture of SimPortControl.

---

## Table of Contents

- [System Overview](#system-overview)
- [Component Architecture](#component-architecture)
- [Data Flow](#data-flow)
- [Database Schema](#database-schema)
- [Security Architecture](#security-architecture)
- [Deployment Architecture](#deployment-architecture)

---

## System Overview

SimPortControl is a three-tier web application:

1. **Presentation Layer** - Vue.js SPA served by Nginx
2. **Application Layer** - FastAPI REST API
3. **Data Layer** - PostgreSQL database

External integration:
- **Cisco Switch** - SSH connection via Netmiko
- **Let's Encrypt** - SSL certificates via Certbot

---

## Component Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              NGINX (Port 443/80)                             │
│                                                                             │
│  ┌─────────────────────────────┐    ┌─────────────────────────────────────┐ │
│  │     Static Files (Vue.js)   │    │      Reverse Proxy (/api/*)        │ │
│  │     /index.html, /assets/*  │    │      → FastAPI :8000               │ │
│  └─────────────────────────────┘    └─────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FASTAPI APPLICATION                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │   Routers    │  │   Services   │  │    Models    │  │   Schemas    │   │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤  ├──────────────┤   │
│  │ auth.py      │  │ auth.py      │  │ user.py      │  │ user.py      │   │
│  │ users.py     │  │ cisco_ssh.py │  │ simulator.py │  │ simulator.py │   │
│  │ simulators.py│  │ scheduler.py │  │ switch.py    │  │ switch.py    │   │
│  │ switches.py  │  │ ssl.py       │  │ port.py      │  │ port.py      │   │
│  │ ports.py     │  │ encryption.py│  │ log.py       │  │ log.py       │   │
│  │ logs.py      │  └──────────────┘  └──────────────┘  └──────────────┘   │
│  │ system.py    │                                                          │
│  └──────────────┘                                                          │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                         APScheduler                                   │  │
│  │                   (Background Port Timeout Jobs)                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
          │                                              │
          ▼                                              ▼
┌──────────────────────┐                    ┌──────────────────────┐
│     PostgreSQL       │                    │    Cisco Switch      │
│     (Port 5432)      │                    │    (SSH Port 22)     │
├──────────────────────┤                    ├──────────────────────┤
│ • users              │                    │ • Netmiko SSH        │
│ • simulators         │                    │ • interface commands │
│ • switches           │                    │ • shutdown/no shut   │
│ • port_assignments   │                    │ • switchport vlan    │
│ • activity_logs      │                    └──────────────────────┘
└──────────────────────┘
```

---

## Data Flow

### Port Enable Flow

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ Browser │───▶│  Nginx  │───▶│ FastAPI │───▶│PostgreSQL│   │  Cisco  │
│         │    │         │    │         │    │         │    │ Switch  │
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
     │              │              │              │              │
     │  POST /api/ports/1/enable   │              │              │
     │─────────────▶│              │              │              │
     │              │──────────────▶              │              │
     │              │   Verify JWT │              │              │
     │              │   Check role │              │              │
     │              │              │              │              │
     │              │              │  Get port    │              │
     │              │              │  assignment  │              │
     │              │              │─────────────▶│              │
     │              │              │◀─────────────│              │
     │              │              │              │              │
     │              │              │  SSH connect │              │
     │              │              │──────────────┼─────────────▶│
     │              │              │  no shutdown │              │
     │              │              │  switchport  │              │
     │              │              │  access vlan │              │
     │              │              │◀─────────────┼──────────────│
     │              │              │              │              │
     │              │              │  Log activity│              │
     │              │              │─────────────▶│              │
     │              │              │              │              │
     │              │              │  Schedule    │              │
     │              │              │  auto-disable│              │
     │              │              │              │              │
     │              │◀─────────────│              │              │
     │◀─────────────│   200 OK     │              │              │
     │              │              │              │              │
```

### Auto-Disable Flow

```
┌──────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────┐
│  APScheduler │───▶│   FastAPI   │───▶│  PostgreSQL │    │  Cisco  │
│              │    │   Service   │    │             │    │ Switch  │
└──────────────┘    └─────────────┘    └─────────────┘    └─────────┘
       │                   │                  │                │
       │  Trigger job      │                  │                │
       │  (timeout reached)│                  │                │
       │──────────────────▶│                  │                │
       │                   │                  │                │
       │                   │  Get port info   │                │
       │                   │─────────────────▶│                │
       │                   │◀─────────────────│                │
       │                   │                  │                │
       │                   │  SSH connect     │                │
       │                   │──────────────────┼───────────────▶│
       │                   │  shutdown        │                │
       │                   │◀─────────────────┼────────────────│
       │                   │                  │                │
       │                   │  Log activity    │                │
       │                   │  (auto-disable)  │                │
       │                   │─────────────────▶│                │
       │                   │                  │                │
       │◀──────────────────│                  │                │
       │  Job complete     │                  │                │
```

---

## Database Schema

```sql
-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'simtech',  -- 'admin' or 'simtech'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Simulators table
CREATE TABLE simulators (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    short_name VARCHAR(20) NOT NULL,
    icon_path VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User-Simulator assignments (many-to-many)
CREATE TABLE user_simulator_assignments (
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    simulator_id INTEGER REFERENCES simulators(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, simulator_id)
);

-- Switches table
CREATE TABLE switches (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    username VARCHAR(50) NOT NULL,
    password_encrypted TEXT NOT NULL,  -- Fernet encrypted
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Port assignments table
CREATE TABLE port_assignments (
    id SERIAL PRIMARY KEY,
    simulator_id INTEGER REFERENCES simulators(id) ON DELETE CASCADE,
    switch_id INTEGER REFERENCES switches(id) ON DELETE CASCADE,
    port_number VARCHAR(20) NOT NULL,  -- e.g., 'Gi0/1'
    vlan INTEGER NOT NULL DEFAULT 30,
    timeout_hours INTEGER NOT NULL DEFAULT 4,

    -- Current state
    status VARCHAR(20) NOT NULL DEFAULT 'disabled',  -- 'enabled' or 'disabled'
    enabled_at TIMESTAMP,
    auto_disable_at TIMESTAMP,
    enabled_by_user_id INTEGER REFERENCES users(id),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(switch_id, port_number)
);

-- Activity logs table
CREATE TABLE activity_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER REFERENCES users(id),
    simulator_id INTEGER REFERENCES simulators(id),
    port_assignment_id INTEGER REFERENCES port_assignments(id),
    action VARCHAR(20) NOT NULL,  -- 'enable', 'disable', 'auto_disable'
    vlan INTEGER,
    timeout_hours INTEGER,
    details JSONB  -- Additional context
);

-- Indexes
CREATE INDEX idx_activity_logs_timestamp ON activity_logs(timestamp DESC);
CREATE INDEX idx_activity_logs_user ON activity_logs(user_id);
CREATE INDEX idx_activity_logs_simulator ON activity_logs(simulator_id);
CREATE INDEX idx_port_assignments_status ON port_assignments(status);
```

### Entity Relationship Diagram

```
┌─────────────┐       ┌─────────────────────────┐       ┌─────────────┐
│    users    │       │ user_simulator_assignments│      │  simulators │
├─────────────┤       ├─────────────────────────┤       ├─────────────┤
│ id          │◀──────│ user_id                 │──────▶│ id          │
│ username    │       │ simulator_id            │       │ name        │
│ password    │       └─────────────────────────┘       │ short_name  │
│ role        │                                         │ icon_path   │
└─────────────┘                                         └─────────────┘
      │                                                        │
      │                                                        │
      ▼                                                        ▼
┌─────────────┐                                    ┌──────────────────┐
│activity_logs│                                    │ port_assignments │
├─────────────┤                                    ├──────────────────┤
│ id          │                                    │ id               │
│ timestamp   │◀───────────────────────────────────│ simulator_id     │
│ user_id     │                                    │ switch_id        │
│ simulator_id│                                    │ port_number      │
│ port_id     │                                    │ vlan             │
│ action      │                                    │ timeout_hours    │
│ vlan        │                                    │ status           │
│ details     │                                    │ enabled_at       │
└─────────────┘                                    │ auto_disable_at  │
                                                   └──────────────────┘
                                                            │
                                                            ▼
                                                   ┌──────────────────┐
                                                   │     switches     │
                                                   ├──────────────────┤
                                                   │ id               │
                                                   │ name             │
                                                   │ ip_address       │
                                                   │ username         │
                                                   │ password_encrypted│
                                                   └──────────────────┘
```

---

## Security Architecture

### Authentication Flow

```
┌─────────┐                    ┌─────────┐                    ┌─────────┐
│ Browser │                    │ FastAPI │                    │   DB    │
└────┬────┘                    └────┬────┘                    └────┬────┘
     │                              │                              │
     │  POST /api/auth/login        │                              │
     │  {username, password}        │                              │
     │─────────────────────────────▶│                              │
     │                              │  Query user                  │
     │                              │─────────────────────────────▶│
     │                              │◀─────────────────────────────│
     │                              │                              │
     │                              │  Verify bcrypt hash          │
     │                              │                              │
     │                              │  Generate JWT                │
     │                              │  (SECRET_KEY, 1hr expiry)    │
     │                              │                              │
     │  {access_token, user}        │                              │
     │◀─────────────────────────────│                              │
     │                              │                              │
     │  Store token in localStorage │                              │
     │                              │                              │
     │  GET /api/simulators         │                              │
     │  Authorization: Bearer xxx   │                              │
     │─────────────────────────────▶│                              │
     │                              │  Decode & verify JWT         │
     │                              │  Check expiration            │
     │                              │  Extract user claims         │
     │                              │                              │
     │  {simulators: [...]}         │                              │
     │◀─────────────────────────────│                              │
```

### Credential Encryption

Switch credentials are encrypted using Fernet (symmetric encryption):

```python
from cryptography.fernet import Fernet

# On application start, load key from environment
ENCRYPTION_KEY = os.environ['ENCRYPTION_KEY']
fernet = Fernet(ENCRYPTION_KEY)

# Storing password
encrypted = fernet.encrypt(password.encode())
# Store 'encrypted' in database

# Retrieving password
decrypted = fernet.decrypt(encrypted).decode()
# Use 'decrypted' for SSH connection
```

### Authorization Matrix

| Endpoint | Admin | SimTech |
|----------|-------|---------|
| `GET /api/simulators` | All | Assigned only |
| `POST /api/ports/*/enable` | All | Assigned only |
| `GET /api/users` | Yes | No |
| `POST /api/switches` | Yes | No |
| `GET /api/logs` | Yes | No |
| `GET /api/system/*` | Yes | No |

---

## Deployment Architecture

### Docker Compose Stack

```yaml
services:
  nginx:
    # Reverse proxy + static files
    ports: ["443:443", "80:80"]
    volumes:
      - ./frontend/dist:/usr/share/nginx/html
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - letsencrypt:/etc/letsencrypt

  app:
    # FastAPI application
    build: ./backend
    environment:
      - DATABASE_URL=postgresql://...
      - SECRET_KEY=...
      - ENCRYPTION_KEY=...
    depends_on: [db]

  db:
    # PostgreSQL database
    image: postgres:16-alpine
    volumes:
      - db_data:/var/lib/postgresql/data

  certbot:
    # SSL certificate management
    image: certbot/certbot
    volumes:
      - letsencrypt:/etc/letsencrypt
      - certbot_data:/var/www/certbot
```

### Network Topology

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              LXC Container                                   │
│                          (simportcontrol.loft.aero)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                        Docker Network (bridge)                        │ │
│  │                                                                       │ │
│  │  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────────────────┐  │ │
│  │  │  nginx  │   │   app   │   │   db    │   │      certbot        │  │ │
│  │  │ :443:80 │◀─▶│  :8000  │◀─▶│ :5432   │   │ (periodic renewal)  │  │ │
│  │  └─────────┘   └─────────┘   └─────────┘   └─────────────────────┘  │ │
│  │       │                           │                                   │ │
│  │       │                           │  Volume: db_data                  │ │
│  │       │                           └──────────────────────────────────▶│ │
│  │       │                                                               │ │
│  │       │  Volume: letsencrypt                                          │ │
│  │       └──────────────────────────────────────────────────────────────▶│ │
│  │                                                                       │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│       │                                                                     │
│       │ Host port mapping                                                   │
└───────┼─────────────────────────────────────────────────────────────────────┘
        │
        │ :443, :80
        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Network                                         │
│                                                                             │
│  ┌─────────────┐                                      ┌─────────────┐      │
│  │   Users     │◀────────────────────────────────────▶│Cisco Switch │      │
│  │  (Browser)  │            HTTPS :443                │  SSH :22    │      │
│  └─────────────┘                                      └─────────────┘      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```
