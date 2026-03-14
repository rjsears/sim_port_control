# Troubleshooting Guide

This guide helps diagnose and resolve common issues with SimPortControl.

---

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Connection Issues](#connection-issues)
- [Authentication Issues](#authentication-issues)
- [Port Control Issues](#port-control-issues)
- [SSL Certificate Issues](#ssl-certificate-issues)
- [Database Issues](#database-issues)
- [Docker Issues](#docker-issues)
- [Log Locations](#log-locations)

---

## Quick Diagnostics

Run these commands to quickly assess system health:

```bash
# Check all containers are running
docker compose ps

# View recent logs
docker compose logs --tail=50

# Check API health
curl -s https://simportcontrol.loft.aero/api/health | jq

# Test database connection
docker compose exec db pg_isready -U simportcontrol

# Check disk space
df -h
```

---

## Connection Issues

### Cannot Access Web Interface

| Symptom | Possible Cause | Solution |
|---------|----------------|----------|
| Connection refused | Nginx not running | `docker compose up -d nginx` |
| Connection timeout | Firewall blocking | Check firewall rules for 443/80 |
| DNS error | DNS not configured | Verify A record exists |
| SSL error | Certificate expired | Run `./scripts/cert_setup.sh` |

**Diagnostic steps:**

```bash
# Check if nginx is running
docker compose ps nginx

# Check nginx logs
docker compose logs nginx --tail=50

# Test local connectivity
curl -v http://localhost:80
curl -vk https://localhost:443

# Test from outside
curl -v https://simportcontrol.loft.aero
```

### Cannot Connect to Cisco Switch

| Symptom | Possible Cause | Solution |
|---------|----------------|----------|
| Connection timeout | Network path blocked | Verify routing from container to switch |
| Authentication failed | Wrong credentials | Check username/password in database |
| SSH version mismatch | Old SSH version | Ensure switch has `ip ssh version 2` |
| Key exchange failure | Incompatible algorithms | Update Netmiko or switch IOS |

**Diagnostic steps:**

```bash
# Test SSH from container
docker compose exec app python -c "
from netmiko import ConnectHandler
device = {
    'device_type': 'cisco_ios',
    'host': '10.0.1.1',
    'username': 'simportcontrol',
    'password': 'your-password',
}
conn = ConnectHandler(**device)
print(conn.send_command('show version'))
conn.disconnect()
"

# Test network path
docker compose exec app ping -c 3 10.0.1.1

# Check switch SSH status (from switch CLI)
# show ip ssh
# show ssh
```

---

## Authentication Issues

### Cannot Login

| Symptom | Possible Cause | Solution |
|---------|----------------|----------|
| "Invalid credentials" | Wrong password | Reset password via database |
| "Invalid credentials" | User doesn't exist | Check user exists in database |
| Token expired | Session timeout | Login again |
| 500 error on login | Database down | Check database container |

**Reset admin password:**

```bash
# Generate new password hash
docker compose exec app python -c "
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
print(pwd_context.hash('new-password'))
"

# Update in database
docker compose exec db psql -U simportcontrol -d simportcontrol -c \
  "UPDATE users SET password_hash='<hash-from-above>' WHERE username='admin';"
```

### Token Issues

| Symptom | Possible Cause | Solution |
|---------|----------------|----------|
| "Token expired" | Session timeout | Login again |
| "Invalid token" | SECRET_KEY changed | All users must re-login |
| 401 on all requests | Token not sent | Check frontend localStorage |

---

## Port Control Issues

### Port Won't Enable

| Symptom | Possible Cause | Solution |
|---------|----------------|----------|
| "Switch connection failed" | SSH error | See [Cannot Connect to Cisco Switch](#cannot-connect-to-cisco-switch) |
| "Permission denied" | User not assigned | Assign simulator to user |
| "Port already enabled" | Duplicate request | Refresh page |
| No response | Timeout | Check network latency to switch |

**Manual port enable (for testing):**

```bash
# SSH to switch and enable manually
ssh simportcontrol@10.0.1.1
configure terminal
interface Gi0/1
no shutdown
switchport access vlan 30
end
show interface status
```

### Port Won't Disable

| Symptom | Possible Cause | Solution |
|---------|----------------|----------|
| SSH timeout | Network issue | Check switch connectivity |
| Command rejected | Port in use | Check spanning-tree state |
| Auto-disable not working | Scheduler not running | Check APScheduler logs |

**Check scheduler:**

```bash
# View scheduler jobs
docker compose exec app python -c "
from app.services.scheduler import scheduler
for job in scheduler.get_jobs():
    print(f'{job.id}: {job.next_run_time}')
"

# Check scheduler logs
docker compose logs app | grep -i scheduler
```

### VLAN Assignment Issues

| Symptom | Possible Cause | Solution |
|---------|----------------|----------|
| Wrong VLAN | Incorrect config | Update port assignment |
| VLAN not allowed | Trunk mode | Set port to access mode |
| VLAN doesn't exist | VLAN not created | Create VLAN on switch |

---

## SSL Certificate Issues

### Certificate Expired

```bash
# Check expiration
docker compose exec certbot certbot certificates

# Force renewal
docker compose exec certbot certbot renew --force-renewal
docker compose exec nginx nginx -s reload
```

### Certificate Not Trusted

| Symptom | Possible Cause | Solution |
|---------|----------------|----------|
| Browser warning | Staging cert | Request production cert |
| Invalid chain | Missing intermediates | Use fullchain.pem |
| Self-signed | Certbot failed | Re-run cert_setup.sh |

### Renewal Failing

```bash
# Test renewal
docker compose exec certbot certbot renew --dry-run

# Check certbot logs
docker compose logs certbot

# Manual renewal
docker compose exec certbot certbot certonly \
  --webroot -w /var/www/certbot \
  -d simportcontrol.loft.aero \
  --force-renewal
```

---

## Database Issues

### Connection Failed

```bash
# Check database is running
docker compose ps db

# Check database logs
docker compose logs db

# Test connection
docker compose exec db pg_isready -U simportcontrol

# Connect manually
docker compose exec db psql -U simportcontrol -d simportcontrol
```

### Database Corrupted

```bash
# Stop all services
docker compose down

# Backup existing data (if possible)
docker compose up -d db
docker compose exec db pg_dump -U simportcontrol simportcontrol > backup.sql

# Reset database
docker compose down -v  # WARNING: Deletes all data!
docker compose up -d

# Re-run migrations
docker compose exec app alembic upgrade head
```

### Migrations Failed

```bash
# Check migration status
docker compose exec app alembic current

# View migration history
docker compose exec app alembic history

# Run pending migrations
docker compose exec app alembic upgrade head

# Rollback one migration
docker compose exec app alembic downgrade -1
```

---

## Docker Issues

### Container Won't Start

```bash
# Check container status
docker compose ps -a

# View container logs
docker compose logs <container-name>

# Rebuild container
docker compose build --no-cache <container-name>
docker compose up -d <container-name>
```

### Out of Disk Space

```bash
# Check disk usage
df -h

# Clean Docker resources
docker system prune -a

# Remove old images
docker image prune -a

# Check container sizes
docker system df
```

### Container Keeps Restarting

```bash
# Check restart count
docker compose ps

# View logs for crash reason
docker compose logs <container-name> --tail=100

# Check resource limits
docker stats
```

---

## Log Locations

### Docker Logs

```bash
# All containers
docker compose logs

# Specific container
docker compose logs app
docker compose logs nginx
docker compose logs db

# Follow logs in real-time
docker compose logs -f app

# Last N lines
docker compose logs --tail=100 app
```

### Application Logs

| Log | Location | Description |
|-----|----------|-------------|
| FastAPI | `docker compose logs app` | API requests, errors |
| Nginx | `docker compose logs nginx` | HTTP access, errors |
| PostgreSQL | `docker compose logs db` | Database queries, errors |
| Certbot | `docker compose logs certbot` | SSL operations |

### Log Levels

Set log level in `.env`:

```bash
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

---

## Getting Help

If you can't resolve an issue:

1. **Collect diagnostics:**
   ```bash
   docker compose ps > diagnostics.txt
   docker compose logs >> diagnostics.txt
   docker system df >> diagnostics.txt
   ```

2. **Open an issue:** [GitHub Issues](https://github.com/rjsears/sim_port_control/issues)

3. **Include:**
   - Error messages (exact text)
   - Steps to reproduce
   - Environment details (OS, Docker version)
   - Relevant log excerpts
