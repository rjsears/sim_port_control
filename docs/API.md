# SimPortControl API Reference

This document provides complete API documentation for SimPortControl.

---

## Table of Contents

- [Authentication](#authentication)
- [Endpoints](#endpoints)
  - [Auth](#auth)
  - [Users](#users)
  - [Simulators](#simulators)
  - [Switches](#switches)
  - [Port Assignments](#port-assignments)
  - [Ports](#ports)
  - [Activity Logs](#activity-logs)
  - [System](#system)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)

---

## Authentication

SimPortControl uses JWT (JSON Web Token) authentication.

### Obtaining a Token

```bash
POST /api/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "your-password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": 1,
    "username": "admin",
    "role": "admin"
  }
}
```

### Using the Token

Include the token in the Authorization header:

```bash
GET /api/simulators
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

---

## Endpoints

### Auth

#### Login
```
POST /api/auth/login
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| username | string | Yes | Username |
| password | string | Yes | Password |

#### Logout
```
POST /api/auth/logout
Authorization: Bearer <token>
```

#### Get Current User
```
GET /api/auth/me
Authorization: Bearer <token>
```

---

### Users

> **Note**: Admin role required for all user management endpoints.

#### List Users
```
GET /api/users
Authorization: Bearer <token>
```

#### Get User
```
GET /api/users/{user_id}
Authorization: Bearer <token>
```

#### Create User
```
POST /api/users
Authorization: Bearer <token>
Content-Type: application/json

{
  "username": "simtech1",
  "password": "secure-password",
  "role": "simtech",
  "assigned_simulators": [1, 2, 3]
}
```

#### Update User
```
PUT /api/users/{user_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "assigned_simulators": [1, 2, 3, 4]
}
```

#### Delete User
```
DELETE /api/users/{user_id}
Authorization: Bearer <token>
```

---

### Simulators

#### List Simulators
```
GET /api/simulators
Authorization: Bearer <token>
```

**Response:**
```json
{
  "simulators": [
    {
      "id": 1,
      "name": "CL350 Challenger 350",
      "short_name": "CL350",
      "icon_path": "/icons/cl350.png",
      "ports": [
        {
          "id": 1,
          "switch_name": "LOFT-SIM-SW01",
          "port_number": "Gi0/1",
          "vlan": 30,
          "timeout_hours": 4,
          "status": "disabled",
          "enabled_at": null,
          "auto_disable_at": null
        }
      ]
    }
  ]
}
```

#### Get Simulator
```
GET /api/simulators/{simulator_id}
Authorization: Bearer <token>
```

#### Create Simulator (Admin)
```
POST /api/simulators
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "CL350 Challenger 350",
  "short_name": "CL350",
  "icon_path": "/icons/cl350.png"
}
```

#### Update Simulator (Admin)
```
PUT /api/simulators/{simulator_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "CL350 Challenger 350 Updated"
}
```

#### Delete Simulator (Admin)
```
DELETE /api/simulators/{simulator_id}
Authorization: Bearer <token>
```

---

### Switches

> **Note**: Admin role required for all switch management endpoints.

#### List Switches
```
GET /api/switches
Authorization: Bearer <token>
```

#### Get Switch
```
GET /api/switches/{switch_id}
Authorization: Bearer <token>
```

#### Create Switch
```
POST /api/switches
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "LOFT-SIM-SW01",
  "ip_address": "10.0.1.1",
  "username": "simportcontrol",
  "password": "switch-password"
}
```

#### Update Switch
```
PUT /api/switches/{switch_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "password": "new-password"
}
```

#### Delete Switch
```
DELETE /api/switches/{switch_id}
Authorization: Bearer <token>
```

#### Test Switch Connection
```
POST /api/switches/{switch_id}/test
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully connected to LOFT-SIM-SW01",
  "switch_info": {
    "hostname": "LOFT-SIM-SW01",
    "model": "WS-C3560G-24PS",
    "ios_version": "15.0(2)SE11"
  }
}
```

---

### Port Assignments

> **Note**: Admin role required for all port assignment endpoints.

#### List Port Assignments
```
GET /api/port-assignments
Authorization: Bearer <token>
```

#### Create Port Assignment
```
POST /api/port-assignments
Authorization: Bearer <token>
Content-Type: application/json

{
  "simulator_id": 1,
  "switch_id": 1,
  "port_number": "Gi0/1",
  "vlan": 30,
  "timeout_hours": 4
}
```

#### Update Port Assignment
```
PUT /api/port-assignments/{assignment_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "timeout_hours": 8,
  "vlan": 40
}
```

#### Delete Port Assignment
```
DELETE /api/port-assignments/{assignment_id}
Authorization: Bearer <token>
```

---

### Ports

#### Get Port Status
```
GET /api/ports/{port_assignment_id}
Authorization: Bearer <token>
```

**Response:**
```json
{
  "id": 1,
  "simulator_name": "CL350 Challenger 350",
  "switch_name": "LOFT-SIM-SW01",
  "port_number": "Gi0/1",
  "vlan": 30,
  "status": "enabled",
  "enabled_at": "2026-03-09T10:30:00Z",
  "auto_disable_at": "2026-03-09T14:30:00Z",
  "enabled_by": "simtech1",
  "seconds_remaining": 7200
}
```

#### Enable Port
```
POST /api/ports/{port_assignment_id}/enable
Authorization: Bearer <token>
Content-Type: application/json

{
  "timeout_hours": 4,
  "vlan": 30
}
```

**Response:**
```json
{
  "success": true,
  "message": "Port Gi0/1 enabled for CL350 Challenger 350",
  "auto_disable_at": "2026-03-09T14:30:00Z"
}
```

#### Disable Port
```
POST /api/ports/{port_assignment_id}/disable
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "message": "Port Gi0/1 disabled for CL350 Challenger 350"
}
```

---

### Activity Logs

#### List Activity Logs (Admin)
```
GET /api/logs
Authorization: Bearer <token>
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| limit | int | Number of records (default: 50, max: 500) |
| offset | int | Pagination offset |
| simulator_id | int | Filter by simulator |
| user_id | int | Filter by user |
| action | string | Filter by action (enable/disable) |
| start_date | datetime | Filter from date |
| end_date | datetime | Filter to date |

**Response:**
```json
{
  "logs": [
    {
      "id": 1,
      "timestamp": "2026-03-09T10:30:00Z",
      "user": "simtech1",
      "simulator": "CL350 Challenger 350",
      "port": "Gi0/1",
      "action": "enable",
      "vlan": 30,
      "timeout_hours": 4
    }
  ],
  "total": 150,
  "limit": 50,
  "offset": 0
}
```

---

### System

#### Health Check
```
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "scheduler": "running"
}
```

#### Get SSL Certificate Info (Admin)
```
GET /api/system/ssl
Authorization: Bearer <token>
```

**Response:**
```json
{
  "configured": true,
  "certificates": [
    {
      "domain": "simportcontrol.loft.aero",
      "valid_from": "2026-01-01T00:00:00Z",
      "valid_until": "2026-04-01T00:00:00Z",
      "days_until_expiry": 23,
      "issuer": "Let's Encrypt Authority X3",
      "status": "valid"
    }
  ]
}
```

#### Force SSL Renewal (Admin)
```
POST /api/system/ssl/renew
Authorization: Bearer <token>
```

#### Get System Info (Admin)
```
GET /api/system/info
Authorization: Bearer <token>
```

**Response:**
```json
{
  "version": "1.0.0",
  "uptime_seconds": 86400,
  "database_size_mb": 12.5,
  "active_ports": 2,
  "total_simulators": 6,
  "total_users": 5
}
```

---

## Error Handling

All errors return a consistent JSON structure:

```json
{
  "detail": "Error message here",
  "error_code": "ERROR_CODE"
}
```

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Invalid or missing token |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found |
| 422 | Validation Error |
| 500 | Internal Server Error |

### Common Error Codes

| Code | Description |
|------|-------------|
| `INVALID_CREDENTIALS` | Username or password incorrect |
| `TOKEN_EXPIRED` | JWT token has expired |
| `PERMISSION_DENIED` | User lacks required role |
| `SWITCH_CONNECTION_FAILED` | Cannot connect to Cisco switch |
| `PORT_ALREADY_ENABLED` | Port is already enabled |
| `SIMULATOR_NOT_ASSIGNED` | SimTech not assigned to this simulator |

---

## Rate Limiting

API endpoints are rate-limited to prevent abuse:

| Endpoint Type | Limit |
|---------------|-------|
| Authentication | 5 requests/minute |
| Port Control | 30 requests/minute |
| Read Operations | 100 requests/minute |

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 25
X-RateLimit-Reset: 1709985600
```
