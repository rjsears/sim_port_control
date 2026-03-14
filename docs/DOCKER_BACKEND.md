# SimPortControl Backend

FastAPI backend for SimPortControl - a web-based switch port management system for flight simulator training facilities.

## Quick Start

```bash
docker pull rjsears/simportcontrol-backend:latest
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_HOST` | PostgreSQL host | Yes |
| `DATABASE_PORT` | PostgreSQL port (default: 5432) | No |
| `DATABASE_NAME` | Database name | Yes |
| `DATABASE_USER` | Database user | Yes |
| `DATABASE_PASSWORD` | Database password | Yes |
| `SECRET_KEY` | JWT signing key | Yes |
| `ENCRYPTION_KEY` | Fernet key for credential encryption | Yes |
| `ADMIN_USERNAME` | Initial admin username | No |
| `ADMIN_PASSWORD` | Initial admin password | No |

## Usage with Docker Compose

See the full [docker-compose.yaml](https://github.com/rjsears/sim_port_control/blob/main/docker-compose.yaml) in the repository.

## Source Code

[https://github.com/rjsears/sim_port_control](https://github.com/rjsears/sim_port_control)
