# SimPortControl Frontend

Vue.js frontend for SimPortControl - a web-based switch port management system for flight simulator training facilities.

## Quick Start

```bash
docker pull rjsears/simportcontrol-frontend:latest
```

## Features

- Vue.js 3 with Composition API
- Tailwind CSS for styling
- Dark/Light mode support
- Mobile-friendly responsive design
- Role-based access (Admin/SimTech)

## Usage

The frontend is typically served through Nginx as part of the full stack. See the [docker-compose.yaml](https://github.com/rjsears/sim_port_control/blob/main/docker-compose.yaml) for the recommended setup.

## Environment

The frontend is a static build. API configuration is set at build time via `VITE_API_URL`.

## Source Code

[https://github.com/rjsears/sim_port_control](https://github.com/rjsears/sim_port_control)
