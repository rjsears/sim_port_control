# =============================================================================
# System Router
# =============================================================================
"""
System status and management endpoints.
"""

import logging
import platform
import socket
from datetime import UTC, datetime

import psutil
from fastapi import APIRouter

from app.config import get_settings
from app.dependencies import AdminUser, DbSession
from app.services.scheduler import get_scheduler_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/system", tags=["System"])
settings = get_settings()


def _get_uptime() -> dict:
    """Get system uptime information."""
    boot_time = datetime.fromtimestamp(psutil.boot_time(), tz=UTC)
    uptime_seconds = (datetime.now(UTC) - boot_time).total_seconds()

    days, remainder = divmod(int(uptime_seconds), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _seconds = divmod(remainder, 60)

    return {
        "boot_time": boot_time.isoformat(),
        "uptime_seconds": int(uptime_seconds),
        "uptime_formatted": f"{days}d {hours}h {minutes}m",
    }


def _get_cpu_info() -> dict:
    """Get CPU information."""
    cpu_percent = psutil.cpu_percent(interval=0.1)
    cpu_count = psutil.cpu_count()
    cpu_count_logical = psutil.cpu_count(logical=True)

    try:
        load_avg = psutil.getloadavg()
    except (AttributeError, OSError):
        load_avg = (0, 0, 0)

    return {
        "percent": cpu_percent,
        "count": cpu_count,
        "count_logical": cpu_count_logical,
        "load_avg_1m": round(load_avg[0], 2),
        "load_avg_5m": round(load_avg[1], 2),
        "load_avg_15m": round(load_avg[2], 2),
    }


def _get_memory_info() -> dict:
    """Get memory information."""
    mem = psutil.virtual_memory()
    return {
        "total_gb": round(mem.total / (1024**3), 2),
        "available_gb": round(mem.available / (1024**3), 2),
        "used_gb": round(mem.used / (1024**3), 2),
        "percent": mem.percent,
    }


def _get_disk_info() -> dict:
    """Get disk information for root partition."""
    try:
        disk = psutil.disk_usage("/")
        return {
            "total_gb": round(disk.total / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "percent": disk.percent,
        }
    except Exception:
        return {"error": "Unable to read disk info"}


def _get_network_info() -> dict:
    """Get network interface information."""
    interfaces = []
    try:
        hostname = socket.gethostname()
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()

        for iface_name, addr_list in addrs.items():
            # Skip loopback and virtual interfaces
            if iface_name == "lo" or iface_name.startswith(("veth", "br-", "docker")):
                continue

            iface_info = {
                "name": iface_name,
                "is_up": False,
                "addresses": [],
            }

            if iface_name in stats:
                iface_info["is_up"] = stats[iface_name].isup

            for addr in addr_list:
                if addr.family == socket.AF_INET:
                    iface_info["addresses"].append(
                        {
                            "type": "ipv4",
                            "address": addr.address,
                            "netmask": addr.netmask,
                        }
                    )
                elif addr.family == socket.AF_INET6 and not addr.address.startswith("fe80"):
                    # Skip link-local IPv6
                    iface_info["addresses"].append(
                        {
                            "type": "ipv6",
                            "address": addr.address,
                        }
                    )

            if iface_info["addresses"]:
                interfaces.append(iface_info)

        return {
            "hostname": hostname,
            "interfaces": interfaces,
        }
    except Exception as e:
        logger.warning(f"Failed to get network info: {e}")
        return {"hostname": "unknown", "interfaces": []}


@router.get("/health")
async def health_check() -> dict:
    """
    Basic health check endpoint.

    Does not require authentication.
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/info")
async def get_system_info(db: DbSession, admin: AdminUser) -> dict:
    """
    Get system information (admin only).

    Returns application version, database status, scheduler info, and system metrics.
    """
    from sqlalchemy import func, select

    from app.models.port_assignment import PortAssignment
    from app.models.simulator import Simulator
    from app.models.user import User

    # Get counts
    simulator_count = await db.scalar(select(func.count()).select_from(Simulator))
    user_count = await db.scalar(select(func.count()).select_from(User))
    active_ports = await db.scalar(
        select(func.count()).select_from(PortAssignment).where(PortAssignment.status == "enabled")
    )

    # Get scheduler jobs
    scheduler = get_scheduler_service()
    scheduled_jobs = scheduler.get_scheduled_jobs()

    # Get system metrics
    uptime = _get_uptime()
    cpu = _get_cpu_info()
    memory = _get_memory_info()
    disk = _get_disk_info()
    network = _get_network_info()

    return {
        "version": "1.0.0",
        "environment": settings.app_env,
        "domain": settings.domain,
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "uptime": uptime,
        "resources": {
            "cpu": cpu,
            "memory": memory,
            "disk": disk,
        },
        "network": network,
        "database": {
            "status": "connected",
            "simulators": simulator_count,
            "users": user_count,
            "active_ports": active_ports,
        },
        "scheduler": {
            "status": "running" if scheduler.scheduler.running else "stopped",
            "pending_jobs": len(scheduled_jobs),
            "jobs": scheduled_jobs,
        },
    }


def _parse_cert_output(output: str, domain: str, cert_path: str) -> dict:
    """Parse openssl x509 output into certificate info dict."""
    cert_info = {
        "domain": domain,
        "path": cert_path,
        "type": "Let's Encrypt",
    }

    for line in output.split("\n"):
        line = line.strip()
        if line.startswith("subject="):
            cert_info["subject"] = line.replace("subject=", "").strip()
        elif line.startswith("issuer="):
            cert_info["issuer"] = line.replace("issuer=", "").strip()
        elif line.startswith("notBefore="):
            cert_info["valid_from"] = line.replace("notBefore=", "").strip()
        elif line.startswith("notAfter="):
            valid_until = line.replace("notAfter=", "").strip()
            cert_info["valid_until"] = valid_until
            try:
                # Parse date like "Mar 12 01:48:00 2026 GMT"
                expiry = datetime.strptime(valid_until, "%b %d %H:%M:%S %Y %Z")
                days_left = (expiry.replace(tzinfo=None) - datetime.now()).days
                cert_info["days_until_expiry"] = days_left
                cert_info["status"] = "valid" if days_left > 0 else "expired"
                if days_left <= 7:
                    cert_info["warning"] = "Certificate expiring soon!"
                elif days_left <= 30:
                    cert_info["warning"] = "Certificate expires within 30 days"
            except Exception:
                pass

    return cert_info


@router.get("/ssl")
async def get_ssl_info(admin: AdminUser) -> dict:
    """
    Get SSL certificate information (admin only).

    Uses Docker SDK to read certificate info from certbot container.
    """
    ssl_info = {
        "configured": False,
        "certificates": [],
    }

    try:
        import docker

        client = docker.from_env()

        # Find certbot container
        certbot_container = None
        for container in client.containers.list():
            if "certbot" in container.name.lower():
                certbot_container = container
                break

        if not certbot_container:
            ssl_info["error"] = "Certbot container not found"
            return ssl_info

        # List certificate directories
        try:
            exit_code, output = certbot_container.exec_run("ls /etc/letsencrypt/live/", demux=True)

            if exit_code == 0 and output[0]:
                domains = output[0].decode("utf-8").strip().split("\n")
                domains = [d.strip() for d in domains if d.strip() and not d.startswith("README")]

                for domain in domains:
                    cert_path = f"/etc/letsencrypt/live/{domain}/fullchain.pem"

                    # Get certificate info using openssl
                    exit_code, cert_output = certbot_container.exec_run(
                        f"openssl x509 -in {cert_path} -noout -subject -issuer -dates", demux=True
                    )

                    if exit_code == 0 and cert_output[0]:
                        cert_str = cert_output[0].decode("utf-8")
                        cert_info = _parse_cert_output(cert_str, domain, cert_path)
                        ssl_info["certificates"].append(cert_info)

                ssl_info["configured"] = len(ssl_info["certificates"]) > 0

        except Exception as e:
            logger.warning(f"Failed to list certificates: {e}")
            ssl_info["error"] = str(e)

    except ImportError:
        ssl_info["error"] = "Docker SDK not installed"
    except Exception as e:
        logger.error(f"Error reading SSL info: {e}")
        ssl_info["error"] = str(e)

    return ssl_info


def _do_ssl_renewal(dry_run: bool = False) -> dict:
    """Run SSL renewal synchronously (called from thread pool)."""
    import docker

    result = {
        "success": False,
        "message": "",
        "renewal_output": "",
        "nginx_reloaded": False,
        "dry_run": dry_run,
    }

    try:
        client = docker.from_env()

        # Find certbot container
        certbot_container = None
        nginx_container = None
        for container in client.containers.list():
            name = container.name.lower()
            if "certbot" in name:
                certbot_container = container
            elif "nginx" in name:
                nginx_container = container

        if not certbot_container:
            result["message"] = "Certbot container not found. Is it running?"
            return result

        if certbot_container.status != "running":
            result["message"] = (
                f"Certbot container is not running (status: {certbot_container.status})"
            )
            return result

        # Build certbot command
        # --force-renewal: Force renewal even if cert is not due
        # --no-random-sleep-on-renew: Skip random delay (up to 8 min) for API calls
        # --deploy-hook true: Override any saved deploy hook with a no-op
        cmd = "certbot renew --force-renewal --no-random-sleep-on-renew --deploy-hook true"
        if dry_run:
            cmd += " --dry-run"

        logger.info(f"Running certbot command: {cmd}")

        exec_result = certbot_container.exec_run(
            cmd=cmd,
            demux=True,
        )

        stdout = exec_result.output[0].decode("utf-8") if exec_result.output[0] else ""
        stderr = exec_result.output[1].decode("utf-8") if exec_result.output[1] else ""
        result["renewal_output"] = stdout + stderr

        if exec_result.exit_code != 0:
            result["message"] = f"Certificate renewal failed (exit code {exec_result.exit_code})"
            return result

        # Reload nginx (skip if dry run)
        if not dry_run and nginx_container and nginx_container.status == "running":
            reload_result = nginx_container.exec_run(cmd="nginx -s reload", demux=True)
            if reload_result.exit_code == 0:
                result["nginx_reloaded"] = True

        result["success"] = True
        if dry_run:
            result["message"] = "Dry run completed successfully (no changes made)"
        else:
            result["message"] = "Certificate renewal completed successfully"

    except Exception as e:
        result["message"] = str(e)

    return result


@router.post("/ssl/renew")
async def renew_ssl_certificate(admin: AdminUser, dry_run: bool = False) -> dict:
    """
    Force SSL certificate renewal (admin only).

    Uses Docker SDK to run certbot renew in the certbot container.

    Args:
        dry_run: If True, test renewal without making changes
    """
    import asyncio

    logger.info(f"Starting SSL certificate renewal (dry_run={dry_run})...")

    try:
        result = await asyncio.to_thread(_do_ssl_renewal, dry_run)

        if result["success"]:
            logger.info("Certificate renewal completed successfully")
        else:
            logger.error(f"Certbot renewal failed: {result['message']}")

        return result

    except Exception as e:
        logger.error(f"SSL renewal failed: {e}")
        return {
            "success": False,
            "message": str(e),
            "renewal_output": "",
            "nginx_reloaded": False,
            "dry_run": dry_run,
        }
