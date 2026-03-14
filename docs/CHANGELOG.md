# Changelog

All notable changes to SimPortControl will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Initial project setup
- Project documentation structure
- README with comprehensive documentation

---

## [1.0.0] - TBD

### Added
- FastAPI backend with JWT authentication
- Vue.js 3 frontend with Tailwind CSS
- PostgreSQL database with SQLAlchemy ORM
- Cisco switch SSH control via Netmiko
- Automatic port timeout with APScheduler
- Role-based access control (Admin/SimTech)
- SSL certificate management with Certbot
- Docker Compose deployment
- Activity logging for all port changes
- Mobile-responsive interface

### Security
- Fernet encryption for switch credentials
- bcrypt password hashing
- JWT token authentication
- HTTPS-only access

---

[Unreleased]: https://github.com/rjsears/sim_port_control/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/rjsears/sim_port_control/releases/tag/v1.0.0
