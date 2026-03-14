#!/bin/bash
# =============================================================================
# SimPortControl SSL Certificate Setup
# =============================================================================
# Obtains Let's Encrypt SSL certificate using HTTP-01 challenge
#
# Usage: ./scripts/cert_setup.sh
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_header() {
    echo -e "\n${CYAN}┌─────────────────────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${CYAN}│${NC} ${BLUE}$1${NC}"
    echo -e "${CYAN}└─────────────────────────────────────────────────────────────────────────────┘${NC}"
}

print_success() { echo -e "  ${GREEN}✓${NC} $1"; }
print_error() { echo -e "  ${RED}✗${NC} $1"; }
print_info() { echo -e "  ${BLUE}ℹ${NC} $1"; }
print_warning() { echo -e "  ${YELLOW}⚠${NC} $1"; }

# Load environment
load_env() {
    if [ -f .env ]; then
        source .env
    else
        print_error ".env file not found. Run setup.sh first."
        exit 1
    fi
}

# Check DNS resolution
check_dns() {
    print_header "Checking DNS"

    print_info "Resolving ${DOMAIN}..."

    resolved_ip=$(dig +short "${DOMAIN}" | head -n 1)

    if [ -z "$resolved_ip" ]; then
        print_error "DNS lookup failed for ${DOMAIN}"
        echo ""
        echo "  Ensure you have an A record pointing to your server's IP address."
        echo ""
        exit 1
    fi

    print_success "${DOMAIN} resolves to ${resolved_ip}"
}

# Check HTTP connectivity
check_http() {
    print_header "Testing HTTP Connectivity"

    print_info "Checking port 80..."

    # Make sure nginx is running with HTTP
    if ! docker compose ps nginx | grep -q "Up"; then
        print_warning "Nginx not running, starting..."
        docker compose up -d nginx
        sleep 5
    fi

    # Test local HTTP
    if curl -s -o /dev/null -w "%{http_code}" "http://localhost/.well-known/acme-challenge/test" | grep -q "404\|200"; then
        print_success "HTTP endpoint accessible"
    else
        print_error "Cannot reach HTTP endpoint"
        print_info "Make sure port 80 is open and forwarded to this server"
        exit 1
    fi
}

# Get email for certificate
get_email() {
    if [ -z "$CERTBOT_EMAIL" ]; then
        read -p "  Enter email for Let's Encrypt notifications: " CERTBOT_EMAIL
    fi

    if [ -z "$CERTBOT_EMAIL" ]; then
        print_error "Email is required for Let's Encrypt"
        exit 1
    fi
}

# Request certificate
request_certificate() {
    print_header "Requesting SSL Certificate"

    print_info "Requesting certificate for ${DOMAIN}..."

    docker compose run --rm certbot certonly \
        --webroot \
        -w /var/www/certbot \
        -d "${DOMAIN}" \
        --email "${CERTBOT_EMAIL}" \
        --agree-tos \
        --non-interactive \
        --force-renewal

    if [ $? -eq 0 ]; then
        print_success "Certificate obtained successfully"
    else
        print_error "Failed to obtain certificate"
        exit 1
    fi
}

# Reload nginx
reload_nginx() {
    print_header "Configuring Nginx"

    print_info "Reloading Nginx with SSL..."
    docker compose exec nginx nginx -s reload
    print_success "Nginx reloaded"
}

# Verify certificate
verify_certificate() {
    print_header "Verifying Certificate"

    sleep 3

    cert_info=$(docker compose exec certbot certbot certificates 2>/dev/null || echo "")

    if echo "$cert_info" | grep -q "${DOMAIN}"; then
        print_success "Certificate is active"

        # Extract expiry
        expiry=$(echo "$cert_info" | grep "Expiry Date" | head -n 1 | cut -d: -f2- | xargs)
        print_info "Expires: ${expiry}"
    else
        print_warning "Could not verify certificate status"
    fi
}

# Summary
print_summary() {
    print_header "Setup Complete!"

    echo ""
    echo "  Certificate: /etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
    echo "  Private Key: /etc/letsencrypt/live/${DOMAIN}/privkey.pem"
    echo ""
    echo "  Auto-renewal is enabled (checks every 12 hours)"
    echo ""
    echo "  Your site is now available at: https://${DOMAIN}"
    echo ""
}

# Main
main() {
    echo -e "${CYAN}"
    echo "┌─────────────────────────────────────────────────────────────────────────────┐"
    echo "│                     SimPortControl SSL Certificate Setup                    │"
    echo "└─────────────────────────────────────────────────────────────────────────────┘"
    echo -e "${NC}"

    load_env
    check_dns
    check_http
    get_email
    request_certificate
    reload_nginx
    verify_certificate
    print_summary
}

main "$@"
