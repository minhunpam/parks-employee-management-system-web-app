# Current state

- When user makes a request on the browser on port 8000. Since inside the Nginx containter, there has existed a port mapping: `8000:80`, that request continues being sent to port `80` which is the port Nginx is listening to internally
- The request can:
  - either contain the URI: `/static/`
  - the rest
- For requests with `/static/`, Nginx serves files from its static-files volumne and cached publicly for the duration of 7 days (According to the Nginx configuration file)
- For requests without `/static/`, requests will be sent to port `8000` which is the one `web` container has exposed to another services in the compose network for communication

## Multiple compose files to separate development and production configurations
- Both configurations share a mutual configuration, `compose.yaml`. This file contains both enviroments need: all the services (Django, PostgreSQL, Nginx), internal service networking, shared volumes, health checks
- `compose.dev.yaml` --- Local development differences, contains: local `.env`, port mappings for PostgreSQL and the app
```
# Run this command in `/src/`
docker compose --env-file ../.env -f ./compose.yaml -f ./compose.dev.yaml -p parks-dev up -d --build
```

- `compose.prod.yaml` --- production differences, contains: production `.env`, `DEBUG=False`, production domain, production secrets, no public PostgreSQL port, production restart policies
```
docker compose --env-file /etc/parks/production.env -f src/compose.yaml -f src/compose.prod.yaml -p parks-dev up -d --build
```

- production environment variables and secrets
- HTTPS configuration
- DNS for app.parks-graz.at
- SSH/firewall hardening
- off-site backups
- GitHub Actions deployment workflow
