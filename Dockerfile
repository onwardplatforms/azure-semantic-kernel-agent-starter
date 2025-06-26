# Multi-stage Dockerfile for Azure Semantic Kernel Agent Starter

# Stage 1: Build .NET Goodbye Agent
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS dotnet-build
WORKDIR /app
COPY agents/goodbye_agent/ ./agents/goodbye_agent/
RUN cd agents/goodbye_agent && dotnet restore
RUN cd agents/goodbye_agent && dotnet publish -c Release -o out

# Stage 2: Build Node.js UI
FROM node:18-alpine AS node-build
WORKDIR /app
COPY ui/package*.json ./
RUN npm ci
COPY ui/ ./
RUN npm run build

# Stage 3: Final runtime image
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Install .NET runtime for goodbye agent
RUN wget https://packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb -O packages-microsoft-prod.deb \
    && dpkg -i packages-microsoft-prod.deb \
    && apt-get update \
    && apt-get install -y aspnetcore-runtime-8.0 \
    && rm packages-microsoft-prod.deb \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy Python requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Python source code
COPY . .

# Copy built .NET application
COPY --from=dotnet-build /app/agents/goodbye_agent/out ./agents/goodbye_agent/

# Copy built UI
COPY --from=node-build /app/.next ./ui/.next
COPY --from=node-build /app/node_modules ./ui/node_modules
COPY --from=node-build /app/package.json ./ui/package.json

# Create supervisor configuration
RUN mkdir -p /etc/supervisor/conf.d

# Create supervisor configuration for all services
COPY <<EOF /etc/supervisor/conf.d/supervisord.conf
[supervisord]
nodaemon=true
user=root
logfile=/var/log/supervisor/supervisord.log
pidfile=/var/run/supervisord.pid

[program:hello_agent]
command=python agents/hello_agent/hello_agent.py
directory=/app
autostart=true
autorestart=true
stderr_logfile=/var/log/hello_agent.err.log
stdout_logfile=/var/log/hello_agent.out.log
environment=PORT="5001"

[program:goodbye_agent]
command=dotnet agents/goodbye_agent/GoodbyeAgent.dll
directory=/app
autostart=true
autorestart=true
stderr_logfile=/var/log/goodbye_agent.err.log
stdout_logfile=/var/log/goodbye_agent.out.log
environment=ASPNETCORE_URLS="http://0.0.0.0:5002"

[program:math_agent]
command=python agents/math_agent/math_agent.py
directory=/app
autostart=true
autorestart=true
stderr_logfile=/var/log/math_agent.err.log
stdout_logfile=/var/log/math_agent.out.log
environment=PORT="5004"

[program:runtime_api]
command=python -m uvicorn api.enhanced_runtime_api:app --host 0.0.0.0 --port 5003
directory=/app
autostart=true
autorestart=true
stderr_logfile=/var/log/runtime_api.err.log
stdout_logfile=/var/log/runtime_api.out.log

[program:mcp_server]
command=python -m uvicorn mcp_server.server:app --host 0.0.0.0 --port 5005
directory=/app
autostart=true
autorestart=true
stderr_logfile=/var/log/mcp_server.err.log
stdout_logfile=/var/log/mcp_server.out.log

[program:ui_server]
command=npm start
directory=/app/ui
autostart=true
autorestart=true
stderr_logfile=/var/log/ui_server.err.log
stdout_logfile=/var/log/ui_server.out.log
environment=PORT="3000"
EOF

# Create database directory
RUN mkdir -p /app/data

# Create entrypoint script
COPY <<EOF /app/entrypoint.sh
#!/bin/bash
set -e

# Initialize database
echo "Initializing database..."
python -c "from database import init_db_sync; init_db_sync()"

# Start supervisor
echo "Starting all services..."
exec supervisord -c /etc/supervisor/conf.d/supervisord.conf
EOF

RUN chmod +x /app/entrypoint.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5003/health || exit 1

# Expose ports
EXPOSE 3000 5001 5002 5003 5004 5005

# Environment variables
ENV PYTHONPATH=/app
ENV DATABASE_URL=sqlite+aiosqlite:///./data/app.db
ENV SYNC_DATABASE_URL=sqlite:///./data/app.db
ENV CONTAINER_MODE=true

# Volume for persistent data
VOLUME ["/app/data"]

# Start the application
ENTRYPOINT ["/app/entrypoint.sh"]