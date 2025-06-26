#!/usr/bin/env python3

"""Main application entry point for running all services."""

import asyncio
import logging
import multiprocessing
import os
import signal
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from typing import List, Optional

import uvicorn
from config import get_settings
from database import init_db_sync

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("main")

settings = get_settings()


class ServiceManager:
    """Manages multiple services in a single container."""
    
    def __init__(self):
        self.processes: List[subprocess.Popen] = []
        self.shutdown_event = asyncio.Event()
        
    def start_agent_service(self, agent_name: str, port: int, script_path: str) -> subprocess.Popen:
        """Start an agent service."""
        env = os.environ.copy()
        env['PORT'] = str(port)
        
        if agent_name == "goodbye_agent":
            # .NET agent
            cwd = f"agents/{agent_name}"
            process = subprocess.Popen(
                ["dotnet", "run"],
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        else:
            # Python agent
            process = subprocess.Popen(
                [sys.executable, script_path],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        
        logger.info(f"Started {agent_name} on port {port} (PID: {process.pid})")
        return process
    
    async def start_fastapi_service(self, app_module: str, host: str, port: int):
        """Start a FastAPI service using uvicorn."""
        config = uvicorn.Config(
            app_module,
            host=host,
            port=port,
            log_level="info",
            access_log=True
        )
        server = uvicorn.Server(config)
        
        logger.info(f"Starting FastAPI service {app_module} on {host}:{port}")
        await server.serve()
    
    def start_all_services(self):
        """Start all services."""
        logger.info("Starting all services...")
        
        # Initialize database
        logger.info("Initializing database...")
        init_db_sync()
        
        # Start agents
        services = [
            ("hello_agent", 5001, "agents/hello_agent/hello_agent.py"),
            ("goodbye_agent", 5002, None),  # .NET service
            ("math_agent", 5004, "agents/math_agent/math_agent.py"),
        ]
        
        for agent_name, port, script_path in services:
            try:
                process = self.start_agent_service(agent_name, port, script_path)
                self.processes.append(process)
                time.sleep(2)  # Give each service time to start
            except Exception as e:
                logger.error(f"Failed to start {agent_name}: {e}")
        
        # Start FastAPI services asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Create tasks for FastAPI services
        tasks = [
            loop.create_task(self.start_fastapi_service(
                "api.enhanced_runtime_api:app",
                settings.api_host,
                settings.api_port
            )),
            loop.create_task(self.start_fastapi_service(
                "mcp_server.server:MCPServer().app",
                settings.mcp_server_host,
                settings.mcp_server_port
            ))
        ]
        
        # Handle shutdown gracefully
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            self.shutdown_all_services()
            for task in tasks:
                task.cancel()
            loop.stop()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            # Run the event loop
            loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            self.shutdown_all_services()
            loop.close()
    
    def shutdown_all_services(self):
        """Shutdown all services gracefully."""
        logger.info("Shutting down all services...")
        
        for process in self.processes:
            if process.poll() is None:  # Process is still running
                logger.info(f"Terminating process {process.pid}")
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    logger.warning(f"Force killing process {process.pid}")
                    process.kill()
        
        self.processes.clear()
        logger.info("All services shut down")
    
    def check_service_health(self) -> bool:
        """Check if all services are healthy."""
        import requests
        
        endpoints = [
            f"http://localhost:5001/health",  # Hello agent
            f"http://localhost:5002/health",  # Goodbye agent  
            f"http://localhost:5004/health",  # Math agent
            f"http://localhost:{settings.api_port}/health",  # Runtime API
            f"http://localhost:{settings.mcp_server_port}/health",  # MCP server
        ]
        
        for endpoint in endpoints:
            try:
                response = requests.get(endpoint, timeout=5)
                if response.status_code != 200:
                    logger.warning(f"Service {endpoint} returned {response.status_code}")
                    return False
            except Exception as e:
                logger.warning(f"Service {endpoint} health check failed: {e}")
                return False
        
        return True


def run_single_service(service_name: str):
    """Run a single service (for development)."""
    if service_name == "runtime":
        uvicorn.run(
            "api.enhanced_runtime_api:app",
            host=settings.api_host,
            port=settings.api_port,
            reload=True
        )
    elif service_name == "mcp":
        from mcp_server.server import MCPServer
        server = MCPServer()
        server.run()
    elif service_name == "ui":
        # For UI, we'd need to run npm run dev
        subprocess.run(["npm", "run", "dev"], cwd="ui")
    else:
        logger.error(f"Unknown service: {service_name}")
        sys.exit(1)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Azure Semantic Kernel Agent Starter")
    parser.add_argument(
        "--service",
        choices=["all", "runtime", "mcp", "ui"],
        default="all",
        help="Service to run (default: all)"
    )
    parser.add_argument(
        "--health-check",
        action="store_true",
        help="Check health of all services and exit"
    )
    
    args = parser.parse_args()
    
    if args.health_check:
        manager = ServiceManager()
        healthy = manager.check_service_health()
        print("All services healthy" if healthy else "Some services unhealthy")
        sys.exit(0 if healthy else 1)
    
    if args.service == "all":
        manager = ServiceManager()
        manager.start_all_services()
    else:
        run_single_service(args.service)


if __name__ == "__main__":
    main()