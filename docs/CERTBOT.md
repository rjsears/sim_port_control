# SSL Certificate Management

This guide covers SSL certificate management for SimPortControl using Let's Encrypt and Certbot.

---

## Table of Contents

- [Overview](#overview)
- [Initial Setup](#initial-setup)
- [Certificate Renewal](#certificate-renewal)
- [Troubleshooting](#troubleshooting)
- [Manual Operations](#manual-operations)

---

## Overview

SimPortControl uses Let's Encrypt for free, automated SSL certificates. The setup uses HTTP-01 challenge validation, which requires:

- Port 80 accessible from the internet (for validation)
- Port 443 for serving HTTPS traffic
- Valid DNS record pointing to your server

---

## Initial Setup

### Prerequisites

1. **Domain configured**: `simportcontrol.loft.aero` points to your server's IP
2. **Ports open**: 80 and 443 accessible from the internet
3. **Docker running**: All containers should be up

### Running cert_setup.sh

```bash
./scripts/cert_setup.sh
```

The script will:

1. **Verify DNS resolution**
   ```
   Checking DNS for simportcontrol.loft.aero...
   ✓ Domain resolves to 203.0.113.50
   ```

2. **Test HTTP connectivity**
   ```
   Testing HTTP access on port 80...
   ✓ Port 80 is accessible
   ```

3. **Request certificate**
   ```
   Requesting certificate from Let's Encrypt...
   ✓ Certificate obtained successfully
   ```

4. **Configure Nginx**
   ```
   Updating Nginx configuration...
   ✓ Nginx reloaded with new certificate
   ```

5. **Set up auto-renewal**
   ```
   Configuring automatic renewal...
   ✓ Renewal cron job installed
   ```

### Expected Output

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     SimPortControl SSL Certificate Setup                     │
└─────────────────────────────────────────────────────────────────────────────┘

Domain: simportcontrol.loft.aero
Email: admin@loft.aero

[1/5] Checking DNS resolution...
  ✓ simportcontrol.loft.aero resolves to 203.0.113.50

[2/5] Testing HTTP connectivity...
  ✓ Port 80 accessible from internet

[3/5] Requesting certificate from Let's Encrypt...
  Saving debug log to /var/log/letsencrypt/letsencrypt.log
  Requesting a certificate for simportcontrol.loft.aero
  Successfully received certificate.
  ✓ Certificate obtained

[4/5] Configuring Nginx...
  ✓ SSL configuration updated
  ✓ Nginx reloaded

[5/5] Setting up auto-renewal...
  ✓ Renewal scheduled (checks every 12 hours)

┌─────────────────────────────────────────────────────────────────────────────┐
│                            Setup Complete!                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  Certificate: /etc/letsencrypt/live/simportcontrol.loft.aero/fullchain.pem │
│  Private Key: /etc/letsencrypt/live/simportcontrol.loft.aero/privkey.pem   │
│  Expires: 2026-06-07                                                        │
│  Auto-renewal: Enabled                                                       │
└─────────────────────────────────────────────────────────────────────────────┘

Your site is now available at: https://simportcontrol.loft.aero
```

---

## Certificate Renewal

### Automatic Renewal

Certbot automatically renews certificates when they have less than 30 days remaining. The renewal check runs every 12 hours via the certbot container.

### Check Renewal Status

```bash
# View certificate expiration
docker compose exec certbot certbot certificates

# Test renewal (dry run)
docker compose exec certbot certbot renew --dry-run
```

### Force Renewal

**Via Web Interface:**
1. Login as admin
2. Navigate to Admin → System
3. Click "Force Renew" button

**Via Command Line:**
```bash
docker compose exec certbot certbot renew --force-renewal
docker compose exec nginx nginx -s reload
```

---

## Troubleshooting

### Common Issues

#### DNS Not Resolving

```
✗ DNS lookup failed for simportcontrol.loft.aero
```

**Solution:**
- Verify DNS A record exists
- Wait for DNS propagation (up to 48 hours)
- Test with: `dig simportcontrol.loft.aero`

#### Port 80 Not Accessible

```
✗ Port 80 is not accessible from the internet
```

**Solution:**
- Check firewall rules
- Verify port forwarding (if behind NAT)
- Ensure nginx container is running

#### Rate Limited

```
Error: too many certificates already issued for this domain
```

**Solution:**
- Wait 1 week (Let's Encrypt rate limit)
- Use staging environment for testing:
  ```bash
  docker compose exec certbot certbot certonly \
    --staging \
    --webroot -w /var/www/certbot \
    -d simportcontrol.loft.aero
  ```

#### Certificate Not Trusted

Browser shows "Your connection is not private"

**Solution:**
- Ensure fullchain.pem is used (includes intermediate certs)
- Check Nginx config points to correct certificate path
- Clear browser cache and retry

---

## Manual Operations

### View Certificate Details

```bash
# Certificate info
docker compose exec certbot certbot certificates

# OpenSSL inspection
docker compose exec nginx openssl x509 \
  -in /etc/letsencrypt/live/simportcontrol.loft.aero/fullchain.pem \
  -text -noout
```

### Revoke Certificate

```bash
docker compose exec certbot certbot revoke \
  --cert-path /etc/letsencrypt/live/simportcontrol.loft.aero/cert.pem
```

### Delete Certificate

```bash
docker compose exec certbot certbot delete \
  --cert-name simportcontrol.loft.aero
```

### Request New Certificate Manually

```bash
docker compose exec certbot certbot certonly \
  --webroot \
  -w /var/www/certbot \
  -d simportcontrol.loft.aero \
  --email admin@loft.aero \
  --agree-tos \
  --non-interactive
```

---

## File Locations

| File | Purpose |
|------|---------|
| `/etc/letsencrypt/live/simportcontrol.loft.aero/fullchain.pem` | Certificate + intermediates |
| `/etc/letsencrypt/live/simportcontrol.loft.aero/privkey.pem` | Private key |
| `/etc/letsencrypt/live/simportcontrol.loft.aero/cert.pem` | Certificate only |
| `/etc/letsencrypt/live/simportcontrol.loft.aero/chain.pem` | Intermediate certificates |
| `/var/log/letsencrypt/letsencrypt.log` | Certbot logs |

---

## Nginx SSL Configuration

Example SSL configuration in `nginx/nginx.conf`:

```nginx
server {
    listen 443 ssl http2;
    server_name simportcontrol.loft.aero;

    ssl_certificate /etc/letsencrypt/live/simportcontrol.loft.aero/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/simportcontrol.loft.aero/privkey.pem;

    # Modern SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # ... rest of configuration
}

# HTTP to HTTPS redirect
server {
    listen 80;
    server_name simportcontrol.loft.aero;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}
```
