#!/bin/bash
# =============================================================================
# SimPortControl Setup Script
# =============================================================================
# Interactive setup for SimPortControl deployment
# Automated SSL certificate setup with Let's Encrypt DNS challenge
#
# Version 2.0.0
# Richard J. Sears
# https://github.com/rjsears
#
# Usage: ./setup.sh
#        ./setup.sh --auto-confirm    # Non-interactive mode
#        ./setup.sh --resume          # Resume interrupted install
# =============================================================================

set -e

# =============================================================================
# CONFIGURATION & CONSTANTS
# =============================================================================

SCRIPT_VERSION="2.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_FILE="${SCRIPT_DIR}/.setup_state"
BACKUP_DIR="${SCRIPT_DIR}/backups"
MAX_BACKUPS=10

# Docker Hub settings (hardcoded)
DOCKER_HUB_USERNAME="rjsears"
IMAGE_TAG="latest"

# Default container names
DEFAULT_POSTGRES_CONTAINER="simportcontrol_db"
DEFAULT_APP_CONTAINER="simportcontrol_app"
DEFAULT_FRONTEND_CONTAINER="simportcontrol_frontend_init"
DEFAULT_NGINX_CONTAINER="simportcontrol_nginx"
DEFAULT_CERTBOT_CONTAINER="simportcontrol_certbot"

# Default settings
DEFAULT_DOMAIN="simportcontrol.loft.aero"
DEFAULT_TIMEZONE="America/Los_Angeles"
DEFAULT_TIMEOUT_HOURS="4"
DEFAULT_VLAN="30"

# System requirements
MIN_DISK_GB=5
MIN_MEMORY_GB=2

# Step tracking
CURRENT_STEP=0
TOTAL_STEPS=10

# Auto-confirm mode (set via --auto-confirm flag or environment)
AUTO_CONFIRM="${AUTO_CONFIRM:-false}"

# Detect the real user (handles both direct execution and sudo ./setup.sh)
if [ -n "$SUDO_USER" ]; then
    REAL_USER="$SUDO_USER"
elif [ -n "$USER" ]; then
    REAL_USER="$USER"
else
    REAL_USER=$(whoami)
fi

# =============================================================================
# COLORS & STYLING
# =============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
GRAY='\033[0;37m'
DIM='\033[2m'
NC='\033[0m'
BOLD='\033[1m'

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

print_header() {
    local title="$1"
    echo ""
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${WHITE}${BOLD}$title${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_section() {
    local title="$1"
    echo ""
    echo -e "${BLUE}┌─────────────────────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${BLUE}│${NC} ${WHITE}${BOLD}$title${NC}"
    echo -e "${BLUE}└─────────────────────────────────────────────────────────────────────────────┘${NC}"
}

print_subsection() {
    echo ""
    echo -e "${GRAY}───────────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
}

print_step() {
    local message="$1"
    ((CURRENT_STEP++)) || true  # Prevent set -e exit when CURRENT_STEP starts at 0
    echo ""
    echo -e "${MAGENTA}[${CURRENT_STEP}/${TOTAL_STEPS}]${NC} ${WHITE}${BOLD}$message${NC}"
    echo -e "${GRAY}───────────────────────────────────────────────────────────────────────────────${NC}"
}

print_success() { echo -e "${GREEN}  ✓${NC} $1"; }
print_error() { echo -e "${RED}  ✗${NC} $1"; }
print_warning() { echo -e "${YELLOW}  ⚠${NC} $1"; }
print_info() { echo -e "${CYAN}  ℹ${NC} $1"; }

prompt_with_default() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"

    if [ "$AUTO_CONFIRM" = "true" ]; then
        eval "$var_name='$default'"
        print_info "Using default: $default"
        return
    fi

    echo -ne "${WHITE}  $prompt [$default]${NC}: "
    read value

    if [ -z "$value" ]; then
        eval "$var_name='$default'"
    else
        eval "$var_name='$value'"
    fi
}

confirm_prompt() {
    local prompt="$1"
    local default="${2:-y}"

    if [ "$AUTO_CONFIRM" = "true" ]; then
        return 0
    fi

    if [ "$default" = "y" ]; then
        echo -ne "${WHITE}  $prompt [Y/n]${NC}: "
    else
        echo -ne "${WHITE}  $prompt [y/N]${NC}: "
    fi

    read response
    response=${response:-$default}

    case "$response" in
        [yY][eE][sS]|[yY]) return 0 ;;
        *) return 1 ;;
    esac
}

# Numbered menu selection
# Usage: select_from_menu "Choose option" "Option 1" "Option 2" "Option 3"
# Returns: selection in $MENU_SELECTION (1-based index), value in $MENU_VALUE
select_from_menu() {
    local prompt="$1"
    shift
    local options=("$@")
    local count=${#options[@]}

    echo ""
    echo -e "  ${WHITE}$prompt:${NC}"
    echo ""

    for i in "${!options[@]}"; do
        echo -e "    ${CYAN}$((i+1)))${NC} ${options[$i]}"
    done

    echo ""

    MENU_SELECTION=""
    while [[ ! "$MENU_SELECTION" =~ ^[1-9][0-9]*$ ]] || [ "$MENU_SELECTION" -gt "$count" ] || [ "$MENU_SELECTION" -lt 1 ]; do
        echo -ne "${WHITE}  Enter your choice [1-$count]${NC}: "
        read MENU_SELECTION
    done

    MENU_VALUE="${options[$((MENU_SELECTION-1))]}"
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# =============================================================================
# INPUT VALIDATION
# =============================================================================

# Validate domain format
# Returns 0 if valid, 1 if invalid
validate_domain() {
    local domain="$1"
    local pattern='^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)+$'

    if [[ "$domain" =~ $pattern ]]; then
        return 0
    else
        return 1
    fi
}

# Validate email format
# Returns 0 if valid, 1 if invalid
validate_email() {
    local email="$1"
    local pattern='^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    if [[ "$email" =~ $pattern ]]; then
        return 0
    else
        return 1
    fi
}

# =============================================================================
# LXC CONTAINER DETECTION
# =============================================================================

# Detect if running inside an LXC container
is_lxc_container() {
    # Method 1: systemd-detect-virt
    if command_exists systemd-detect-virt; then
        local virt_type
        virt_type=$(systemd-detect-virt 2>/dev/null || echo "none")
        if [ "$virt_type" = "lxc" ]; then
            return 0
        fi
    fi

    # Method 2: Check /proc/1/environ for container=lxc
    if grep -qa 'container=lxc' /proc/1/environ 2>/dev/null; then
        return 0
    fi

    # Method 3: Check for container manager file
    if [ -f /run/host/container-manager ]; then
        return 0
    fi

    return 1
}

show_lxc_warning() {
    echo ""
    echo -e "${RED}╔═══════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║${NC}                          ${YELLOW}${BOLD}LXC CONTAINER DETECTED${NC}                           ${RED}║${NC}"
    echo -e "${RED}╠═══════════════════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${RED}║${NC}                                                                           ${RED}║${NC}"
    echo -e "${RED}║${NC}  ${WHITE}Running Docker inside an LXC container requires special configuration.${NC}  ${RED}║${NC}"
    echo -e "${RED}║${NC}                                                                           ${RED}║${NC}"
    echo -e "${RED}║${NC}  ${CYAN}Required Proxmox LXC Configuration:${NC}                                     ${RED}║${NC}"
    echo -e "${RED}║${NC}                                                                           ${RED}║${NC}"
    echo -e "${RED}║${NC}  ${GRAY}Edit /etc/pve/lxc/<container-id>.conf and add:${NC}                          ${RED}║${NC}"
    echo -e "${RED}║${NC}                                                                           ${RED}║${NC}"
    echo -e "${RED}║${NC}    ${GREEN}features: nesting=1${NC}                                                    ${RED}║${NC}"
    echo -e "${RED}║${NC}    ${GREEN}lxc.apparmor.profile: unconfined${NC}                                       ${RED}║${NC}"
    echo -e "${RED}║${NC}                                                                           ${RED}║${NC}"
    echo -e "${RED}║${NC}  ${GRAY}Then restart the container:${NC}                                              ${RED}║${NC}"
    echo -e "${RED}║${NC}    ${GREEN}pct stop <container-id> && pct start <container-id>${NC}                    ${RED}║${NC}"
    echo -e "${RED}║${NC}                                                                           ${RED}║${NC}"
    echo -e "${RED}║${NC}  ${WHITE}This docker-compose already includes 'apparmor:unconfined' for all${NC}      ${RED}║${NC}"
    echo -e "${RED}║${NC}  ${WHITE}services, but the LXC host must also be configured correctly.${NC}           ${RED}║${NC}"
    echo -e "${RED}║${NC}                                                                           ${RED}║${NC}"
    echo -e "${RED}╚═══════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    if [ "$AUTO_CONFIRM" != "true" ]; then
        if ! confirm_prompt "Have you configured Proxmox as shown above? Continue anyway?"; then
            print_info "Please configure your LXC container and run setup again."
            exit 0
        fi
    else
        print_warning "Auto-confirm mode: Proceeding despite LXC environment"
    fi
}

# =============================================================================
# SYSTEM CHECKS
# =============================================================================

# Run command with sudo only if not root
run_privileged() {
    if [ "$(id -u)" -eq 0 ]; then
        "$@"
    else
        sudo "$@"
    fi
}

# Check available disk space
check_disk_space() {
    local required_gb=$MIN_DISK_GB
    local available_gb=""

    if command_exists df; then
        # Get available space in GB for the script directory
        available_gb=$(df -BG "${SCRIPT_DIR}" 2>/dev/null | awk 'NR==2 {gsub(/G/,"",$4); print $4}' || echo "")

        # Validate that we got a number
        if [ -n "$available_gb" ] && [[ "$available_gb" =~ ^[0-9]+$ ]]; then
            if [ "$available_gb" -ge "$required_gb" ] 2>/dev/null; then
                print_success "Disk space: ${available_gb}GB available (${required_gb}GB required)"
                return 0
            else
                print_warning "Low disk space: ${available_gb}GB available (${required_gb}GB recommended)"
                if [ "$AUTO_CONFIRM" != "true" ]; then
                    if ! confirm_prompt "Continue with limited disk space?"; then
                        exit 1
                    fi
                fi
                return 0
            fi
        fi
    fi

    print_warning "Could not determine disk space"
    return 0
}

# Check available memory
check_memory() {
    local required_gb=$MIN_MEMORY_GB
    local available_gb=""
    local mem_kb=""
    local mem_bytes=""

    if [ -f /proc/meminfo ]; then
        # Linux: Get total memory in GB
        mem_kb=$(grep MemTotal /proc/meminfo 2>/dev/null | awk '{print $2}' || echo "")
        if [ -n "$mem_kb" ] && [[ "$mem_kb" =~ ^[0-9]+$ ]]; then
            available_gb=$((mem_kb / 1024 / 1024))
        fi
    elif command_exists sysctl; then
        # macOS: Get total memory in GB
        mem_bytes=$(sysctl -n hw.memsize 2>/dev/null || echo "")
        if [ -n "$mem_bytes" ] && [[ "$mem_bytes" =~ ^[0-9]+$ ]]; then
            available_gb=$((mem_bytes / 1024 / 1024 / 1024))
        fi
    fi

    if [ -n "$available_gb" ] && [[ "$available_gb" =~ ^[0-9]+$ ]] && [ "$available_gb" -ge "$required_gb" ] 2>/dev/null; then
        print_success "Memory: ${available_gb}GB available (${required_gb}GB required)"
        return 0
    elif [ -n "$available_gb" ] && [[ "$available_gb" =~ ^[0-9]+$ ]]; then
        print_warning "Low memory: ${available_gb}GB available (${required_gb}GB recommended)"
        if [ "$AUTO_CONFIRM" != "true" ]; then
            if ! confirm_prompt "Continue with limited memory?"; then
                exit 1
            fi
        fi
        return 0
    fi

    print_warning "Could not determine available memory"
    return 0
}

# Check if required ports are available
check_port_available() {
    local port=$1
    local in_use=false
    local process_info=""

    # Try ss first (modern Linux)
    if command_exists ss; then
        if ss -tuln 2>/dev/null | grep -q ":${port} "; then
            in_use=true
            process_info=$(ss -tulnp 2>/dev/null | grep ":${port} " | head -1)
        fi
    # Fall back to netstat
    elif command_exists netstat; then
        if netstat -tuln 2>/dev/null | grep -q ":${port} "; then
            in_use=true
            process_info=$(netstat -tulnp 2>/dev/null | grep ":${port} " | head -1)
        fi
    # Fall back to lsof
    elif command_exists lsof; then
        if lsof -i ":${port}" >/dev/null 2>&1; then
            in_use=true
            process_info=$(lsof -i ":${port}" 2>/dev/null | head -2 | tail -1)
        fi
    fi

    if [ "$in_use" = "true" ]; then
        print_warning "Port $port is already in use"
        if [ -n "$process_info" ]; then
            print_info "Process: $process_info"
        fi
        return 1
    else
        print_success "Port $port is available"
        return 0
    fi
}

# Check internet connectivity
check_internet_connectivity() {
    local test_host="hub.docker.com"
    local timeout=5

    print_info "Checking internet connectivity..."

    if command_exists curl; then
        if curl -s --connect-timeout $timeout "https://${test_host}" >/dev/null 2>&1; then
            print_success "Internet connectivity: OK (Docker Hub reachable)"
            return 0
        fi
    elif command_exists wget; then
        if wget -q --timeout=$timeout --spider "https://${test_host}" 2>/dev/null; then
            print_success "Internet connectivity: OK (Docker Hub reachable)"
            return 0
        fi
    fi

    print_warning "Could not reach Docker Hub - you may have connectivity issues"
    print_info "This may cause problems pulling Docker images"

    if [ "$AUTO_CONFIRM" != "true" ]; then
        if ! confirm_prompt "Continue anyway?"; then
            exit 1
        fi
    fi

    return 0
}

# Perform all system checks
perform_system_checks() {
    print_step "System Requirements Check"

    check_disk_space
    check_memory

    print_subsection

    print_info "Checking port availability..."
    local ports_ok=true

    if ! check_port_available 80; then
        ports_ok=false
    fi
    if ! check_port_available 443; then
        ports_ok=false
    fi

    if [ "$ports_ok" = "false" ]; then
        print_warning "Some required ports are in use"
        if [ "$AUTO_CONFIRM" != "true" ]; then
            if ! confirm_prompt "Continue anyway? (existing services may conflict)"; then
                exit 1
            fi
        fi
    fi

    print_subsection

    check_internet_connectivity

    echo ""
    print_success "System checks complete"
}

# =============================================================================
# STATE MANAGEMENT (Resume Capability)
# =============================================================================

save_state() {
    local step="$1"
    cat > "$STATE_FILE" << EOF
# SimPortControl Setup State - Do not edit manually
SETUP_STEP=$step
SETUP_TIMESTAMP=$(date +%s)
SETUP_VERSION=$SCRIPT_VERSION
DOMAIN=${DOMAIN:-}
LETSENCRYPT_EMAIL=${LETSENCRYPT_EMAIL:-}
TIMEZONE=${TIMEZONE:-}
ADMIN_USERNAME=${ADMIN_USERNAME:-}
DNS_PROVIDER=${DNS_PROVIDER:-}
DNS_CERTBOT_IMAGE=${DNS_CERTBOT_IMAGE:-}
DNS_CREDENTIALS_FILE=${DNS_CREDENTIALS_FILE:-}
EOF
    chmod 600 "$STATE_FILE"
}

load_state() {
    if [ -f "$STATE_FILE" ]; then
        source "$STATE_FILE"
        return 0
    fi
    return 1
}

clear_state() {
    rm -f "$STATE_FILE"
}

check_resume() {
    if [ -f "$STATE_FILE" ]; then
        load_state

        local saved_time
        local time_diff
        local time_ago

        saved_time="${SETUP_TIMESTAMP:-0}"
        # Ensure saved_time is numeric
        if ! [[ "$saved_time" =~ ^[0-9]+$ ]]; then
            saved_time=0
        fi
        time_diff=$(($(date +%s) - saved_time))

        if [ $time_diff -lt 3600 ]; then
            time_ago="$((time_diff / 60)) minutes ago"
        elif [ $time_diff -lt 86400 ]; then
            time_ago="$((time_diff / 3600)) hours ago"
        else
            time_ago="$((time_diff / 86400)) days ago"
        fi

        echo ""
        echo -e "${YELLOW}╔═══════════════════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${YELLOW}║${NC}                    ${WHITE}${BOLD}INCOMPLETE INSTALLATION DETECTED${NC}                     ${YELLOW}║${NC}"
        echo -e "${YELLOW}╠═══════════════════════════════════════════════════════════════════════════╣${NC}"
        echo -e "${YELLOW}║${NC}                                                                           ${YELLOW}║${NC}"
        echo -e "${YELLOW}║${NC}  ${WHITE}A previous setup was interrupted at step ${SETUP_STEP}${NC}                           ${YELLOW}║${NC}"
        echo -e "${YELLOW}║${NC}  ${GRAY}Started: ${time_ago}${NC}                                              ${YELLOW}║${NC}"
        echo -e "${YELLOW}║${NC}                                                                           ${YELLOW}║${NC}"
        if [ -n "$DOMAIN" ]; then
        echo -e "${YELLOW}║${NC}  ${WHITE}Domain: ${CYAN}${DOMAIN}${NC}                                             ${YELLOW}║${NC}"
        fi
        echo -e "${YELLOW}║${NC}                                                                           ${YELLOW}║${NC}"
        echo -e "${YELLOW}╚═══════════════════════════════════════════════════════════════════════════╝${NC}"
        echo ""

        if [ "$AUTO_CONFIRM" = "true" ]; then
            print_info "Auto-confirm mode: Starting fresh installation"
            clear_state
            return 1
        fi

        select_from_menu "What would you like to do?" \
            "Resume previous installation" \
            "Start fresh (backup existing config)" \
            "Start fresh (discard previous state)"

        case $MENU_SELECTION in
            1)
                print_info "Resuming from step $SETUP_STEP..."
                CURRENT_STEP=$((SETUP_STEP - 1))
                return 0
                ;;
            2)
                backup_existing_config
                clear_state
                return 1
                ;;
            3)
                clear_state
                return 1
                ;;
        esac
    fi

    return 1
}

# =============================================================================
# BACKUP MANAGEMENT
# =============================================================================

backup_existing_config() {
    print_info "Creating backup of existing configuration..."

    # Create backup directory
    mkdir -p "$BACKUP_DIR"

    # Generate timestamp for backup
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_path="${BACKUP_DIR}/backup_${timestamp}"
    mkdir -p "$backup_path"

    # Backup files if they exist
    local files_backed_up=0

    if [ -f "${SCRIPT_DIR}/.env" ]; then
        cp "${SCRIPT_DIR}/.env" "${backup_path}/"
        ((files_backed_up++)) || true
    fi

    if [ -f "${SCRIPT_DIR}/docker-compose.yaml" ]; then
        cp "${SCRIPT_DIR}/docker-compose.yaml" "${backup_path}/"
        ((files_backed_up++)) || true
    fi

    if [ -f "${SCRIPT_DIR}/cloudflare.ini" ]; then
        cp "${SCRIPT_DIR}/cloudflare.ini" "${backup_path}/"
        ((files_backed_up++)) || true
    fi

    if [ -f "${SCRIPT_DIR}/route53.ini" ]; then
        cp "${SCRIPT_DIR}/route53.ini" "${backup_path}/"
        ((files_backed_up++)) || true
    fi

    if [ -f "${SCRIPT_DIR}/digitalocean.ini" ]; then
        cp "${SCRIPT_DIR}/digitalocean.ini" "${backup_path}/"
        ((files_backed_up++)) || true
    fi

    if [ -f "${SCRIPT_DIR}/google.json" ]; then
        cp "${SCRIPT_DIR}/google.json" "${backup_path}/"
        ((files_backed_up++)) || true
    fi

    # Create manifest
    cat > "${backup_path}/manifest.txt" << EOF
SimPortControl Backup
Created: $(date)
Version: $SCRIPT_VERSION
Files: $files_backed_up
EOF

    if [ $files_backed_up -gt 0 ]; then
        print_success "Backed up $files_backed_up file(s) to: ${backup_path}"
    else
        print_info "No configuration files to backup"
        rmdir "$backup_path" 2>/dev/null || true
    fi

    # Cleanup old backups (keep only last N)
    cleanup_old_backups
}

cleanup_old_backups() {
    local backup_count=$(ls -1d "${BACKUP_DIR}"/backup_* 2>/dev/null | wc -l)

    if [ "$backup_count" -gt "$MAX_BACKUPS" ]; then
        local to_delete=$((backup_count - MAX_BACKUPS))
        print_info "Cleaning up old backups (keeping last $MAX_BACKUPS)..."

        ls -1dt "${BACKUP_DIR}"/backup_* | tail -n "$to_delete" | while read dir; do
            rm -rf "$dir"
        done
    fi
}

list_available_backups() {
    if [ ! -d "$BACKUP_DIR" ]; then
        print_info "No backups found"
        return 1
    fi

    local backups=($(ls -1dt "${BACKUP_DIR}"/backup_* 2>/dev/null))

    if [ ${#backups[@]} -eq 0 ]; then
        print_info "No backups found"
        return 1
    fi

    echo ""
    echo -e "  ${WHITE}Available backups:${NC}"
    echo ""

    for i in "${!backups[@]}"; do
        local backup_name=$(basename "${backups[$i]}")
        local backup_date=$(echo "$backup_name" | sed 's/backup_//' | sed 's/_/ /')
        local file_count=$(ls -1 "${backups[$i]}" 2>/dev/null | wc -l)
        echo -e "    ${CYAN}$((i+1)))${NC} ${backup_name} (${file_count} files)"
    done

    echo ""
    return 0
}

# =============================================================================
# READ MASKED INPUT
# =============================================================================

# Read sensitive input showing first 10 chars, then masking the rest
# Usage: read_masked_token "prompt"
# Returns: value in $MASKED_INPUT
read_masked_token() {
    local prompt="$1"
    MASKED_INPUT=""
    local char=""
    local display=""

    echo -ne "${WHITE}  $prompt${NC}: "

    # Disable echo
    stty -echo

    while IFS= read -r -n1 char; do
        # Check for Enter (empty char)
        if [[ -z "$char" ]]; then
            break
        fi

        # Check for backspace (ASCII 127 or 8)
        if [[ "$char" == $'\x7f' ]] || [[ "$char" == $'\x08' ]]; then
            if [[ -n "$MASKED_INPUT" ]]; then
                MASKED_INPUT="${MASKED_INPUT%?}"
                # Clear line and redisplay
                echo -ne "\r\033[K"
                echo -ne "${WHITE}  $prompt${NC}: "
                local len=${#MASKED_INPUT}
                if [[ $len -le 10 ]]; then
                    echo -ne "$MASKED_INPUT"
                else
                    echo -ne "${MASKED_INPUT:0:10}$(printf '%*s' $((len - 10)) '' | tr ' ' '*')"
                fi
            fi
            continue
        fi

        # Add character to input
        MASKED_INPUT+="$char"

        # Display: first 10 chars visible, rest as *
        local len=${#MASKED_INPUT}
        if [[ $len -le 10 ]]; then
            echo -ne "$char"
        else
            echo -ne "*"
        fi
    done

    # Re-enable echo
    stty echo
    echo ""
}

# =============================================================================
# OS DETECTION & PACKAGE MANAGEMENT
# =============================================================================

detect_os() {
    DISTRO=""
    DISTRO_FAMILY=""
    PKG_MANAGER=""
    PKG_UPDATE=""
    PKG_INSTALL=""

    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
        DISTRO_VERSION=$VERSION_ID
    elif [ -f /etc/debian_version ]; then
        DISTRO="debian"
    elif [ -f /etc/redhat-release ]; then
        DISTRO="rhel"
    fi

    case $DISTRO in
        ubuntu|debian|linuxmint|pop|raspbian)
            DISTRO_FAMILY="debian"
            PKG_MANAGER="apt-get"
            PKG_UPDATE="apt-get update -qq"
            PKG_INSTALL="apt-get install -y -qq"
            ;;
        centos|rhel|rocky|almalinux|ol)
            DISTRO_FAMILY="rhel"
            if command_exists dnf; then
                PKG_MANAGER="dnf"
                PKG_UPDATE="dnf check-update || true"
                PKG_INSTALL="dnf install -y"
            else
                PKG_MANAGER="yum"
                PKG_UPDATE="yum check-update || true"
                PKG_INSTALL="yum install -y"
            fi
            ;;
        fedora)
            DISTRO_FAMILY="fedora"
            PKG_MANAGER="dnf"
            PKG_UPDATE="dnf check-update || true"
            PKG_INSTALL="dnf install -y"
            ;;
        opensuse*|sles)
            DISTRO_FAMILY="suse"
            PKG_MANAGER="zypper"
            PKG_UPDATE="zypper refresh"
            PKG_INSTALL="zypper install -y"
            ;;
        arch|manjaro)
            DISTRO_FAMILY="arch"
            PKG_MANAGER="pacman"
            PKG_UPDATE="pacman -Sy"
            PKG_INSTALL="pacman -S --noconfirm"
            ;;
        alpine)
            DISTRO_FAMILY="alpine"
            PKG_MANAGER="apk"
            PKG_UPDATE="apk update"
            PKG_INSTALL="apk add"
            ;;
        *)
            # Fallback detection
            if command_exists apt-get; then
                DISTRO_FAMILY="debian"
                PKG_MANAGER="apt-get"
                PKG_UPDATE="apt-get update -qq"
                PKG_INSTALL="apt-get install -y -qq"
            elif command_exists dnf; then
                DISTRO_FAMILY="rhel"
                PKG_MANAGER="dnf"
                PKG_UPDATE="dnf check-update || true"
                PKG_INSTALL="dnf install -y"
            elif command_exists yum; then
                DISTRO_FAMILY="rhel"
                PKG_MANAGER="yum"
                PKG_UPDATE="yum check-update || true"
                PKG_INSTALL="yum install -y"
            elif command_exists zypper; then
                DISTRO_FAMILY="suse"
                PKG_MANAGER="zypper"
                PKG_UPDATE="zypper refresh"
                PKG_INSTALL="zypper install -y"
            elif command_exists pacman; then
                DISTRO_FAMILY="arch"
                PKG_MANAGER="pacman"
                PKG_UPDATE="pacman -Sy"
                PKG_INSTALL="pacman -S --noconfirm"
            fi
            ;;
    esac

    return 0
}

# =============================================================================
# INSTALL MISSING UTILITIES
# =============================================================================

install_utility() {
    local util="$1"
    print_info "Installing $util..."

    run_privileged $PKG_UPDATE >/dev/null 2>&1 || true
    run_privileged $PKG_INSTALL "$util" >/dev/null 2>&1

    if command_exists "$util"; then
        print_success "$util installed successfully"
        return 0
    else
        print_error "Failed to install $util"
        return 1
    fi
}

# =============================================================================
# DOCKER INSTALLATION
# =============================================================================

install_docker_linux() {
    print_info "Installing Docker..."
    echo ""

    case $DISTRO_FAMILY in
        debian)
            print_info "Detected Debian/Ubuntu-based system"

            # Remove old versions
            run_privileged apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

            # Install prerequisites
            run_privileged apt-get update
            run_privileged apt-get install -y ca-certificates curl gnupg lsb-release

            # Add Docker GPG key
            run_privileged install -m 0755 -d /etc/apt/keyrings
            curl -fsSL "https://download.docker.com/linux/$DISTRO/gpg" | run_privileged gpg --dearmor -o /etc/apt/keyrings/docker.gpg
            run_privileged chmod a+r /etc/apt/keyrings/docker.gpg

            # Add Docker repository
            echo \
                "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$DISTRO \
                $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
                run_privileged tee /etc/apt/sources.list.d/docker.list > /dev/null

            # Install Docker
            run_privileged apt-get update
            run_privileged apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
            ;;
        rhel|fedora)
            print_info "Detected RHEL/CentOS/Fedora-based system"

            run_privileged yum remove -y docker docker-client docker-client-latest docker-common docker-latest docker-latest-logrotate docker-logrotate docker-engine 2>/dev/null || true
            run_privileged yum install -y yum-utils
            run_privileged yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
            run_privileged yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
            ;;
        suse)
            print_info "Detected openSUSE/SLES system"
            run_privileged zypper install -y docker docker-compose
            ;;
        arch)
            print_info "Detected Arch-based system"
            run_privileged pacman -S --noconfirm docker docker-compose
            ;;
        *)
            print_error "Unsupported distribution: $DISTRO"
            print_info "Please install Docker manually: https://docs.docker.com/engine/install/"
            exit 1
            ;;
    esac

    # Start and enable Docker
    run_privileged systemctl start docker
    run_privileged systemctl enable docker

    # Add current user to docker group
    if [ -n "$REAL_USER" ] && [ "$REAL_USER" != "root" ]; then
        run_privileged usermod -aG docker "$REAL_USER"
        print_warning "Added $REAL_USER to docker group. You may need to log out and back in."
    fi

    print_success "Docker installed successfully!"
    local docker_version=$(docker --version 2>/dev/null | cut -d' ' -f3 | tr -d ',')
    print_success "Docker version: $docker_version"
}

# =============================================================================
# PREREQUISITE CHECKS
# =============================================================================

check_and_install_prerequisites() {
    print_step "Checking Prerequisites"

    detect_os

    if [ -z "$PKG_MANAGER" ]; then
        print_error "Could not detect package manager"
        exit 1
    fi

    print_info "Detected: $DISTRO ($DISTRO_FAMILY)"
    echo ""

    # Check curl
    if command_exists curl; then
        print_success "curl is installed"
    else
        print_warning "curl is not installed"
        if [ "$AUTO_CONFIRM" = "true" ] || confirm_prompt "Install curl?"; then
            install_utility curl
        else
            print_error "curl is required"
            exit 1
        fi
    fi

    # Check openssl
    if command_exists openssl; then
        print_success "openssl is installed"
    else
        print_warning "openssl is not installed"
        if [ "$AUTO_CONFIRM" = "true" ] || confirm_prompt "Install openssl?"; then
            install_utility openssl
        else
            print_error "openssl is required"
            exit 1
        fi
    fi

    # Check jq (optional)
    if command_exists jq; then
        print_success "jq is installed"
    else
        print_warning "jq is not installed"
        if [ "$AUTO_CONFIRM" = "true" ] || confirm_prompt "Install jq? (recommended)"; then
            install_utility jq
        fi
    fi

    print_subsection

    # Check Docker
    if command_exists docker; then
        local docker_version=$(docker --version 2>/dev/null | cut -d' ' -f3 | tr -d ',')
        print_success "Docker is installed (version: $docker_version)"

        if docker info >/dev/null 2>&1; then
            print_success "Docker daemon is running"
        else
            print_warning "Docker daemon is not running"
            if [ "$AUTO_CONFIRM" = "true" ] || confirm_prompt "Start Docker daemon?"; then
                run_privileged systemctl start docker
                run_privileged systemctl enable docker
                print_success "Docker daemon started"
            else
                print_error "Docker daemon is required"
                exit 1
            fi
        fi
    else
        print_warning "Docker is not installed"
        if [ "$AUTO_CONFIRM" = "true" ] || confirm_prompt "Install Docker?"; then
            install_docker_linux
        else
            print_error "Docker is required"
            exit 1
        fi
    fi

    # Check Docker Compose
    if docker compose version >/dev/null 2>&1; then
        local compose_version=$(docker compose version --short 2>/dev/null)
        print_success "Docker Compose v2 is available (version: $compose_version)"
    else
        print_error "Docker Compose is not available"
        print_info "Docker Compose should be included with Docker. Please reinstall Docker."
        exit 1
    fi

    echo ""
    print_success "All prerequisites satisfied!"

    save_state 2
}

# =============================================================================
# CHECK REQUIRED FILES
# =============================================================================

check_required_files() {
    print_step "Checking Required Files"

    if [ -f "${SCRIPT_DIR}/docker-compose.yaml" ]; then
        print_success "docker-compose.yaml exists"
    else
        print_warning "docker-compose.yaml not found (will be created)"
    fi

    if [ -f "${SCRIPT_DIR}/nginx/nginx.conf" ]; then
        print_success "nginx/nginx.conf exists"
    else
        print_error "nginx/nginx.conf not found"
        print_info "Please ensure nginx configuration exists before continuing"
        exit 1
    fi

    save_state 3
}

# =============================================================================
# DNS PROVIDER CONFIGURATION
# =============================================================================

configure_dns_provider() {
    print_step "SSL Certificate Configuration (DNS Challenge)"

    echo ""
    echo -e "  ${GRAY}Since port 80 is not exposed to the internet, we use DNS challenge.${NC}"
    echo ""

    select_from_menu "Select your DNS provider" \
        "Cloudflare" \
        "Route53 (AWS)" \
        "DigitalOcean" \
        "Google Cloud DNS"

    case $MENU_SELECTION in
        1)
            DNS_PROVIDER="cloudflare"
            DNS_CERTBOT_IMAGE="certbot/dns-cloudflare:latest"
            DNS_CREDENTIALS_FILE="cloudflare.ini"
            DNS_CERTBOT_FLAGS="--dns-cloudflare --dns-cloudflare-credentials /credentials.ini --dns-cloudflare-propagation-seconds 60"
            configure_cloudflare
            ;;
        2)
            DNS_PROVIDER="route53"
            DNS_CERTBOT_IMAGE="certbot/dns-route53:latest"
            DNS_CREDENTIALS_FILE="route53.ini"
            DNS_CERTBOT_FLAGS="--dns-route53"
            configure_route53
            ;;
        3)
            DNS_PROVIDER="digitalocean"
            DNS_CERTBOT_IMAGE="certbot/dns-digitalocean:latest"
            DNS_CREDENTIALS_FILE="digitalocean.ini"
            DNS_CERTBOT_FLAGS="--dns-digitalocean --dns-digitalocean-credentials /credentials.ini --dns-digitalocean-propagation-seconds 60"
            configure_digitalocean
            ;;
        4)
            DNS_PROVIDER="google"
            DNS_CERTBOT_IMAGE="certbot/dns-google:latest"
            DNS_CREDENTIALS_FILE="google.json"
            DNS_CERTBOT_FLAGS="--dns-google --dns-google-credentials /credentials.ini --dns-google-propagation-seconds 60"
            configure_google
            ;;
    esac

    save_state 4
}

configure_cloudflare() {
    echo ""
    print_info "Cloudflare DNS selected"
    echo ""
    echo -e "  ${GRAY}You need a Cloudflare API token with DNS:Edit permissions.${NC}"
    echo -e "  ${GRAY}Create one at: https://dash.cloudflare.com/profile/api-tokens${NC}"
    echo ""

    while [ -z "$CLOUDFLARE_API_TOKEN" ]; do
        read_masked_token "Enter Cloudflare API token"
        CLOUDFLARE_API_TOKEN="$MASKED_INPUT"
        if [ -z "$CLOUDFLARE_API_TOKEN" ]; then
            print_error "API token is required"
        fi
    done

    echo "dns_cloudflare_api_token = $CLOUDFLARE_API_TOKEN" > "${SCRIPT_DIR}/cloudflare.ini"
    chmod 600 "${SCRIPT_DIR}/cloudflare.ini"
    print_success "Cloudflare credentials configured"
}

configure_route53() {
    echo ""
    print_info "AWS Route53 DNS selected"
    echo ""

    while [ -z "$AWS_ACCESS_KEY_ID" ]; do
        read_masked_token "Enter AWS Access Key ID"
        AWS_ACCESS_KEY_ID="$MASKED_INPUT"
    done

    while [ -z "$AWS_SECRET_ACCESS_KEY" ]; do
        read_masked_token "Enter AWS Secret Access Key"
        AWS_SECRET_ACCESS_KEY="$MASKED_INPUT"
    done

    cat > "${SCRIPT_DIR}/route53.ini" << EOF
[default]
aws_access_key_id = $AWS_ACCESS_KEY_ID
aws_secret_access_key = $AWS_SECRET_ACCESS_KEY
EOF
    chmod 600 "${SCRIPT_DIR}/route53.ini"
    print_success "Route53 credentials configured"
}

configure_digitalocean() {
    echo ""
    print_info "DigitalOcean DNS selected"
    echo ""

    while [ -z "$DIGITALOCEAN_TOKEN" ]; do
        read_masked_token "Enter DigitalOcean API token"
        DIGITALOCEAN_TOKEN="$MASKED_INPUT"
    done

    echo "dns_digitalocean_token = $DIGITALOCEAN_TOKEN" > "${SCRIPT_DIR}/digitalocean.ini"
    chmod 600 "${SCRIPT_DIR}/digitalocean.ini"
    print_success "DigitalOcean credentials configured"
}

configure_google() {
    echo ""
    print_info "Google Cloud DNS selected"
    echo ""
    echo -e "  ${GRAY}You need a service account JSON key file with DNS Admin role.${NC}"
    echo ""

    while [ -z "$GOOGLE_CREDENTIALS_PATH" ] || [ ! -f "$GOOGLE_CREDENTIALS_PATH" ]; do
        echo -ne "${WHITE}  Enter path to Google credentials JSON file${NC}: "
        read GOOGLE_CREDENTIALS_PATH
        if [ -n "$GOOGLE_CREDENTIALS_PATH" ] && [ ! -f "$GOOGLE_CREDENTIALS_PATH" ]; then
            print_error "File not found: $GOOGLE_CREDENTIALS_PATH"
            GOOGLE_CREDENTIALS_PATH=""
        fi
    done

    cp "$GOOGLE_CREDENTIALS_PATH" "${SCRIPT_DIR}/google.json"
    chmod 600 "${SCRIPT_DIR}/google.json"
    print_success "Google DNS credentials configured"
}

# =============================================================================
# APPLICATION CONFIGURATION
# =============================================================================

configure_application() {
    print_step "Application Configuration"

    echo ""

    # Check if .env already exists
    if [ -f "${SCRIPT_DIR}/.env" ]; then
        print_warning ".env file already exists"
        if [ "$AUTO_CONFIRM" != "true" ]; then
            if ! confirm_prompt "Overwrite existing configuration?"; then
                print_info "Keeping existing .env file"
                source "${SCRIPT_DIR}/.env"
                save_state 5
                return 0
            fi
        fi
        backup_existing_config
    fi

    # Domain (with validation)
    while true; do
        prompt_with_default "Domain name" "$DEFAULT_DOMAIN" "DOMAIN"
        if validate_domain "$DOMAIN"; then
            print_success "Domain format valid"
            break
        else
            print_error "Invalid domain format. Please enter a valid domain (e.g., example.com)"
            DOMAIN=""
        fi
    done

    # Let's Encrypt email (with validation and confirmation)
    while true; do
        echo -ne "${WHITE}  Email for SSL certificates${NC}: "
        read LETSENCRYPT_EMAIL

        if [ -z "$LETSENCRYPT_EMAIL" ]; then
            print_error "Email is required for Let's Encrypt"
            continue
        fi

        if ! validate_email "$LETSENCRYPT_EMAIL"; then
            print_error "Invalid email format. Please enter a valid email address"
            LETSENCRYPT_EMAIL=""
            continue
        fi

        echo -ne "${WHITE}  Confirm email${NC}: "
        read LETSENCRYPT_EMAIL_CONFIRM

        if [ "$LETSENCRYPT_EMAIL" != "$LETSENCRYPT_EMAIL_CONFIRM" ]; then
            print_error "Emails do not match. Please try again."
            LETSENCRYPT_EMAIL=""
            continue
        fi

        print_success "Email validated"
        break
    done

    # Timezone
    prompt_with_default "Timezone" "$DEFAULT_TIMEZONE" "TIMEZONE"

    print_subsection

    # Admin credentials
    prompt_with_default "Admin username" "admin" "ADMIN_USERNAME"

    # Admin password (with confirmation)
    while true; do
        echo -ne "${WHITE}  Admin password (min 8 chars)${NC}: "
        read -s ADMIN_PASSWORD
        echo ""

        if [ ${#ADMIN_PASSWORD} -lt 8 ]; then
            print_error "Password must be at least 8 characters"
            ADMIN_PASSWORD=""
            continue
        fi

        echo -ne "${WHITE}  Confirm admin password${NC}: "
        read -s ADMIN_PASSWORD_CONFIRM
        echo ""

        if [ "$ADMIN_PASSWORD" != "$ADMIN_PASSWORD_CONFIRM" ]; then
            print_error "Passwords do not match. Please try again."
            ADMIN_PASSWORD=""
            continue
        fi

        print_success "Admin password set"
        break
    done

    print_subsection

    # Database password (auto-generate or manual with confirmation)
    echo -ne "${WHITE}  Database password (Enter to auto-generate)${NC}: "
    read -s DATABASE_PASSWORD
    echo ""

    if [ -z "$DATABASE_PASSWORD" ]; then
        DATABASE_PASSWORD=$(openssl rand -hex 24)
        print_info "Auto-generated database password"
    else
        echo -ne "${WHITE}  Confirm database password${NC}: "
        read -s DATABASE_PASSWORD_CONFIRM
        echo ""
        while [ "$DATABASE_PASSWORD" != "$DATABASE_PASSWORD_CONFIRM" ]; do
            print_error "Passwords do not match. Please try again."
            echo -ne "${WHITE}  Database password${NC}: "
            read -s DATABASE_PASSWORD
            echo ""
            echo -ne "${WHITE}  Confirm database password${NC}: "
            read -s DATABASE_PASSWORD_CONFIRM
            echo ""
        done
        print_success "Database password set"
    fi

    # Generate security keys
    print_info "Generating security keys..."
    SECRET_KEY=$(openssl rand -hex 32)
    ENCRYPTION_KEY=$(openssl rand -base64 32)

    print_success "Configuration complete"

    save_state 5
}

# =============================================================================
# CREATE ENVIRONMENT FILE
# =============================================================================

create_env_file() {
    print_step "Creating Environment File"

    cat > "${SCRIPT_DIR}/.env" << EOF
# =============================================================================
# SimPortControl Environment Configuration
# Generated by setup.sh v${SCRIPT_VERSION} on $(date)
# =============================================================================

# Application
APP_ENV=production
DOMAIN=${DOMAIN}
TIMEZONE=${TIMEZONE}

# Docker Hub
DOCKER_HUB_USERNAME=${DOCKER_HUB_USERNAME}
IMAGE_TAG=${IMAGE_TAG}

# Security
SECRET_KEY=${SECRET_KEY}
ENCRYPTION_KEY=${ENCRYPTION_KEY}

# Database
DATABASE_NAME=simportcontrol
DATABASE_USER=simportcontrol
DATABASE_PASSWORD=${DATABASE_PASSWORD}

# Container Names
POSTGRES_CONTAINER=${DEFAULT_POSTGRES_CONTAINER}
APP_CONTAINER=${DEFAULT_APP_CONTAINER}
FRONTEND_CONTAINER=${DEFAULT_FRONTEND_CONTAINER}
NGINX_CONTAINER=${DEFAULT_NGINX_CONTAINER}
CERTBOT_CONTAINER=${DEFAULT_CERTBOT_CONTAINER}

# Admin User
ADMIN_USERNAME=${ADMIN_USERNAME}
ADMIN_PASSWORD=${ADMIN_PASSWORD}

# SSL/Certbot (DNS Challenge)
LETSENCRYPT_EMAIL=${LETSENCRYPT_EMAIL}
DNS_PROVIDER=${DNS_PROVIDER}
DNS_CERTBOT_IMAGE=${DNS_CERTBOT_IMAGE}
DNS_CREDENTIALS_FILE=${DNS_CREDENTIALS_FILE}
DNS_CERTBOT_FLAGS=${DNS_CERTBOT_FLAGS}

# Default Settings
DEFAULT_TIMEOUT_HOURS=${DEFAULT_TIMEOUT_HOURS}
DEFAULT_VLAN=${DEFAULT_VLAN}
LOG_LEVEL=INFO
EOF

    chmod 600 "${SCRIPT_DIR}/.env"
    print_success "Created .env file (permissions: 600)"

    save_state 6
}

# =============================================================================
# CREATE SSL VOLUME
# =============================================================================

create_ssl_volume() {
    print_step "Setting Up SSL Volume"

    if docker volume inspect letsencrypt &> /dev/null; then
        print_info "letsencrypt volume already exists"
    else
        docker volume create letsencrypt
        print_success "Created letsencrypt external volume"
    fi

    save_state 7
}

# =============================================================================
# UPDATE DOCKER COMPOSE
# =============================================================================

update_docker_compose() {
    print_step "Configuring Docker Compose"

    local compose_file="${SCRIPT_DIR}/docker-compose.yaml"

    # Backup original if it exists
    if [ -f "$compose_file" ]; then
        cp "$compose_file" "${compose_file}.bak"
        print_info "Backed up existing docker-compose.yaml"
    fi

    cat > "$compose_file" << 'EOF'
# =============================================================================
# SimPortControl Docker Compose Configuration
# =============================================================================
# Production deployment using Docker Hub images with DNS-based SSL
# Usage: docker compose up -d

networks:
  simportcontrol:
    driver: bridge

volumes:
  db_data:
  letsencrypt:
    external: true
  certbot_data:
  frontend_dist:

services:
  # ===========================================================================
  # PostgreSQL Database
  # ===========================================================================
  db:
    image: postgres:16-alpine
    container_name: ${POSTGRES_CONTAINER:-simportcontrol_db}
    restart: unless-stopped
    security_opt:
      - apparmor:unconfined
    environment:
      POSTGRES_DB: ${DATABASE_NAME:-simportcontrol}
      POSTGRES_USER: ${DATABASE_USER:-simportcontrol}
      POSTGRES_PASSWORD: ${DATABASE_PASSWORD}
    volumes:
      - db_data:/var/lib/postgresql/data
    networks:
      - simportcontrol
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DATABASE_USER:-simportcontrol}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ===========================================================================
  # FastAPI Backend (from Docker Hub)
  # ===========================================================================
  app:
    image: ${DOCKER_HUB_USERNAME:-rjsears}/simportcontrol-backend:${IMAGE_TAG:-latest}
    container_name: ${APP_CONTAINER:-simportcontrol_app}
    restart: unless-stopped
    security_opt:
      - apparmor:unconfined
    environment:
      - APP_ENV=${APP_ENV:-production}
      - DOMAIN=${DOMAIN:-simportcontrol.loft.aero}
      - SECRET_KEY=${SECRET_KEY}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
      - DATABASE_HOST=db
      - DATABASE_PORT=5432
      - DATABASE_NAME=${DATABASE_NAME:-simportcontrol}
      - DATABASE_USER=${DATABASE_USER:-simportcontrol}
      - DATABASE_PASSWORD=${DATABASE_PASSWORD}
      - ADMIN_USERNAME=${ADMIN_USERNAME:-admin}
      - ADMIN_PASSWORD=${ADMIN_PASSWORD}
      - DEFAULT_TIMEOUT_HOURS=${DEFAULT_TIMEOUT_HOURS:-4}
      - DEFAULT_VLAN=${DEFAULT_VLAN:-30}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - TZ=${TIMEZONE:-America/Los_Angeles}
    volumes:
      - letsencrypt:/etc/letsencrypt:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    networks:
      - simportcontrol
    depends_on:
      db:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # ===========================================================================
  # Frontend Init Container - copies static files to shared volume
  # ===========================================================================
  frontend-init:
    image: ${DOCKER_HUB_USERNAME:-rjsears}/simportcontrol-frontend:${IMAGE_TAG:-latest}
    container_name: ${FRONTEND_CONTAINER:-simportcontrol_frontend_init}
    security_opt:
      - apparmor:unconfined
    volumes:
      - frontend_dist:/dist
    entrypoint: ["/bin/sh", "-c"]
    command: ["cp -r /usr/share/nginx/html/* /dist/ && echo 'Frontend files copied successfully'"]
    restart: "no"

  # ===========================================================================
  # Nginx Reverse Proxy
  # ===========================================================================
  nginx:
    image: nginx:alpine
    container_name: ${NGINX_CONTAINER:-simportcontrol_nginx}
    restart: unless-stopped
    security_opt:
      - apparmor:unconfined
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - frontend_dist:/usr/share/nginx/html:ro
      - letsencrypt:/etc/letsencrypt:ro
      - certbot_data:/var/www/certbot:ro
    networks:
      - simportcontrol
    depends_on:
      - app
      - frontend-init
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # ===========================================================================
  # Certbot (Let's Encrypt SSL) - DNS Challenge with Auto-Renewal
  # ===========================================================================
  certbot:
    image: ${DNS_CERTBOT_IMAGE:-certbot/dns-cloudflare:latest}
    container_name: ${CERTBOT_CONTAINER:-simportcontrol_certbot}
    restart: unless-stopped
    security_opt:
      - apparmor:unconfined
    volumes:
      - letsencrypt:/etc/letsencrypt
      - certbot_data:/var/www/certbot
      - ./${DNS_CREDENTIALS_FILE:-cloudflare.ini}:/credentials.ini:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    entrypoint: /bin/sh -c "trap exit TERM; while :; do certbot renew ${DNS_CERTBOT_FLAGS} --deploy-hook 'docker exec ${NGINX_CONTAINER:-simportcontrol_nginx} nginx -s reload' || true; sleep 12h & wait $${!}; done;"
    networks:
      - simportcontrol
EOF

    print_success "docker-compose.yaml configured for DNS challenge"

    save_state 8
}

# =============================================================================
# OBTAIN SSL CERTIFICATE
# =============================================================================

obtain_ssl_certificate() {
    print_step "Obtaining SSL Certificate"

    # Check if certificate already exists
    if docker run --rm -v letsencrypt:/etc/letsencrypt alpine ls "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" &> /dev/null 2>&1; then
        print_success "SSL certificate already exists for ${DOMAIN}"
        save_state 9
        return 0
    fi

    print_info "Obtaining certificate for ${DOMAIN} using ${DNS_PROVIDER} DNS challenge..."
    echo ""
    print_info "This may take a minute while DNS propagates..."
    echo ""

    # Run certbot with DNS challenge
    if docker run --rm \
        --security-opt apparmor:unconfined \
        -v letsencrypt:/etc/letsencrypt \
        -v "${SCRIPT_DIR}/${DNS_CREDENTIALS_FILE}:/credentials.ini:ro" \
        "${DNS_CERTBOT_IMAGE}" certonly \
        ${DNS_CERTBOT_FLAGS} \
        -d "${DOMAIN}" \
        --email "${LETSENCRYPT_EMAIL}" \
        --agree-tos \
        --non-interactive; then
        print_success "SSL certificate obtained successfully!"
    else
        print_error "Failed to obtain SSL certificate"
        print_info "Check your DNS credentials and domain configuration"
        print_info "You can try again by running: ./setup.sh --resume"
        exit 1
    fi

    save_state 9
}

# =============================================================================
# DEPLOY STACK
# =============================================================================

deploy_stack() {
    print_step "Deploying Stack"

    cd "${SCRIPT_DIR}"

    print_info "Pulling Docker images from Docker Hub..."
    docker compose pull

    print_info "Starting containers..."
    docker compose up -d

    print_info "Waiting for services to start..."

    # Poll for health with progress
    local max_attempts=30
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        ((attempt++)) || true
        echo -ne "\r  Checking services... (attempt ${attempt}/${max_attempts})"

        if docker compose ps 2>/dev/null | grep -q "healthy"; then
            echo ""
            break
        fi

        sleep 2
    done

    echo ""
    print_info "Container status:"
    docker compose ps
    echo ""

    if docker compose ps | grep -q "healthy\|running"; then
        print_success "Services are running"
    else
        print_warning "Some services may need more time to start"
        print_info "Check status with: docker compose ps"
    fi

    # Clear state file on successful completion
    clear_state

    save_state 10
}

# =============================================================================
# SHOW COMPLETION SUMMARY
# =============================================================================

show_completion_summary() {
    print_header "Setup Complete"

    echo ""
    echo -e "  ${GREEN}╔═══════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "  ${GREEN}║${NC}                      ${WHITE}${BOLD}INSTALLATION SUCCESSFUL${NC}                        ${GREEN}║${NC}"
    echo -e "  ${GREEN}╚═══════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  ${WHITE}Access the application at:${NC}"
    echo -e "    ${CYAN}https://${DOMAIN}${NC}"
    echo ""
    echo -e "  ${WHITE}Login credentials:${NC}"
    echo -e "    Username: ${CYAN}${ADMIN_USERNAME}${NC}"
    echo -e "    Password: ${GRAY}(the password you entered)${NC}"
    echo ""
    echo -e "  ${WHITE}SSL Certificate:${NC}"
    echo -e "    View status in Admin > System panel"
    echo -e "    Auto-renewal runs every 12 hours via ${DNS_PROVIDER} DNS"
    echo ""
    echo -e "  ${WHITE}Useful commands:${NC}"
    echo -e "    ${GRAY}docker compose logs -f${NC}        # View logs"
    echo -e "    ${GRAY}docker compose ps${NC}             # Check status"
    echo -e "    ${GRAY}docker compose restart${NC}        # Restart services"
    echo -e "    ${GRAY}docker compose down${NC}           # Stop all services"
    echo -e "    ${GRAY}docker compose pull && docker compose up -d${NC}  # Update"
    echo ""

    # Clear state on successful completion
    clear_state
}

# =============================================================================
# PARSE COMMAND LINE ARGUMENTS
# =============================================================================

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --auto-confirm|--yes|-y)
                AUTO_CONFIRM="true"
                shift
                ;;
            --resume)
                # Will be handled by check_resume
                shift
                ;;
            --help|-h)
                echo ""
                echo "SimPortControl Setup Script v${SCRIPT_VERSION}"
                echo ""
                echo "Usage: ./setup.sh [options]"
                echo ""
                echo "Options:"
                echo "  --auto-confirm, -y    Non-interactive mode (use defaults)"
                echo "  --resume              Resume an interrupted installation"
                echo "  --help, -h            Show this help message"
                echo ""
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    parse_args "$@"

    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════════════════════╗"
    echo "║                                                                           ║"
    echo "║                      SimPortControl Setup v${SCRIPT_VERSION}                         ║"
    echo "║                                                                           ║"
    echo "║          Web-based switch port management for flight simulators           ║"
    echo "║                                                                           ║"
    echo "╚═══════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    if [ "$AUTO_CONFIRM" = "true" ]; then
        print_info "Running in auto-confirm mode"
    fi

    # Check if running as root
    if [ "${EUID:-$(id -u)}" -eq 0 ] 2>/dev/null; then
        print_warning "Running as root. Consider using a non-root user with Docker permissions."
    fi

    # Check for LXC container environment
    if is_lxc_container; then
        show_lxc_warning
    fi

    # Check for resume
    local resuming=false
    if check_resume; then
        resuming=true
    fi

    # Run steps (skip completed ones if resuming)
    if [ "$resuming" = "false" ] || [ "$CURRENT_STEP" -lt 1 ]; then
        perform_system_checks
    fi

    if [ "$resuming" = "false" ] || [ "$CURRENT_STEP" -lt 2 ]; then
        check_and_install_prerequisites
    fi

    if [ "$resuming" = "false" ] || [ "$CURRENT_STEP" -lt 3 ]; then
        check_required_files
    fi

    if [ "$resuming" = "false" ] || [ "$CURRENT_STEP" -lt 4 ]; then
        configure_dns_provider
    fi

    if [ "$resuming" = "false" ] || [ "$CURRENT_STEP" -lt 5 ]; then
        configure_application
    fi

    if [ "$resuming" = "false" ] || [ "$CURRENT_STEP" -lt 6 ]; then
        create_env_file
    fi

    if [ "$resuming" = "false" ] || [ "$CURRENT_STEP" -lt 7 ]; then
        create_ssl_volume
    fi

    if [ "$resuming" = "false" ] || [ "$CURRENT_STEP" -lt 8 ]; then
        update_docker_compose
    fi

    if [ "$resuming" = "false" ] || [ "$CURRENT_STEP" -lt 9 ]; then
        obtain_ssl_certificate
    fi

    if [ "$resuming" = "false" ] || [ "$CURRENT_STEP" -lt 10 ]; then
        deploy_stack
    fi

    show_completion_summary
}

main "$@"
