.PHONY: help install dev build run stop clean logs health status docker-build docker-run docker-stop ui-only mcp-only runtime-only

# Default target
.DEFAULT_GOAL := help

# Colors for output
CYAN := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
RESET := \033[0m

help: ## Show this help message
	@echo "$(CYAN)Azure Semantic Kernel Agent Starter$(RESET)"
	@echo "$(CYAN)====================================$(RESET)"
	@echo ""
	@echo "$(GREEN)Available commands:$(RESET)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(CYAN)%-15s$(RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""

install: ## Install Python dependencies
	@echo "$(YELLOW)Installing Python dependencies...$(RESET)"
	pip install -r requirements.txt
	@echo "$(GREEN)✅ Python dependencies installed$(RESET)"

install-ui: ## Install UI dependencies
	@echo "$(YELLOW)Installing UI dependencies...$(RESET)"
	cd ui && npm install
	@echo "$(GREEN)✅ UI dependencies installed$(RESET)"

install-all: install install-ui ## Install all dependencies
	@echo "$(GREEN)✅ All dependencies installed$(RESET)"

dev: ## Run all services in development mode
	@echo "$(YELLOW)Starting all services in development mode...$(RESET)"
	@echo "$(CYAN)Starting core services first...$(RESET)"
	@echo ""
	@echo "$(GREEN)🌐 Starting UI at: http://localhost:3000$(RESET)"
	@echo "$(GREEN)🔧 Runtime API will be at: http://localhost:5003$(RESET)"
	@echo ""
	@cd ui && npm run dev &
	@sleep 3
	@python -m uvicorn api.enhanced_runtime_api:app --host 0.0.0.0 --port 5003 --reload &
	@sleep 3
	@python agents/hello_agent/hello_agent.py &
	@sleep 2
	@python agents/math_agent/math_agent.py &
	@sleep 2
	@echo "$(GREEN)✅ Core services started!$(RESET)"
	@echo "$(CYAN)Press Ctrl+C to stop all services$(RESET)"
	@wait

run: dev ## Alias for dev command

build: ## Build the Docker container
	@echo "$(YELLOW)Building Docker container...$(RESET)"
	docker build -t azure-sk-agent-starter .
	@echo "$(GREEN)✅ Docker container built$(RESET)"

docker-run: build ## Build and run with Docker
	@echo "$(YELLOW)Starting with Docker...$(RESET)"
	docker-compose up -d
	@sleep 10
	@echo ""
	@echo "$(GREEN)🚀 Azure Semantic Kernel Agent Starter (Docker)$(RESET)"
	@echo "$(GREEN)===============================================$(RESET)"
	@echo ""
	@echo "$(GREEN)🌐 UI available at: http://localhost:3000$(RESET)"
	@echo "$(GREEN)🔧 Runtime API at: http://localhost:5003$(RESET)"
	@echo "$(GREEN)🧮 MCP Server at: http://localhost:5005$(RESET)"
	@echo ""
	@echo "$(CYAN)Use 'make docker-stop' to stop services$(RESET)"
	@echo "$(CYAN)Use 'make logs' to view logs$(RESET)"

docker-stop: ## Stop Docker services
	@echo "$(YELLOW)Stopping Docker services...$(RESET)"
	docker-compose down
	@echo "$(GREEN)✅ Docker services stopped$(RESET)"

stop: ## Stop all running services
	@echo "$(YELLOW)Stopping all services...$(RESET)"
	@pkill -f "python main.py" 2>/dev/null || true
	@pkill -f "uvicorn" 2>/dev/null || true
	@pkill -f "hello_agent.py" 2>/dev/null || true
	@pkill -f "math_agent" 2>/dev/null || true
	@pkill -f "dotnet run" 2>/dev/null || true
	@pkill -f "next dev" 2>/dev/null || true
	@pkill -f "npm start" 2>/dev/null || true
	@lsof -ti:3000,5001,5002,5003,5004,5005 | xargs kill -9 2>/dev/null || true
	@echo "$(GREEN)✅ All services stopped$(RESET)"

clean: stop ## Stop services and clean up
	@echo "$(YELLOW)Cleaning up...$(RESET)"
	@rm -f *.log
	@rm -f app.db*
	@docker system prune -f 2>/dev/null || true
	@echo "$(GREEN)✅ Cleanup complete$(RESET)"

logs: ## View Docker logs
	@echo "$(CYAN)Viewing Docker logs (Ctrl+C to exit)...$(RESET)"
	docker-compose logs -f

health: ## Check health of all services
	@echo "$(CYAN)Checking service health...$(RESET)"
	@echo ""
	@curl -s http://localhost:5001/health | jq '.agent_id' 2>/dev/null && echo "$(GREEN)✅ Hello Agent: Healthy$(RESET)" || echo "$(RED)❌ Hello Agent: Unhealthy$(RESET)"
	@curl -s http://localhost:5002/health | jq '.status' 2>/dev/null && echo "$(GREEN)✅ Goodbye Agent: Healthy$(RESET)" || echo "$(RED)❌ Goodbye Agent: Unhealthy$(RESET)"
	@curl -s http://localhost:5004/health | jq '.agent_id' 2>/dev/null && echo "$(GREEN)✅ Math Agent: Healthy$(RESET)" || echo "$(RED)❌ Math Agent: Unhealthy$(RESET)"
	@curl -s http://localhost:5003/health | jq '.status' 2>/dev/null && echo "$(GREEN)✅ Runtime API: Healthy$(RESET)" || echo "$(RED)❌ Runtime API: Unhealthy$(RESET)"
	@curl -s http://localhost:5005/health | jq '.status' 2>/dev/null && echo "$(GREEN)✅ MCP Server: Healthy$(RESET)" || echo "$(RED)❌ MCP Server: Unhealthy$(RESET)"
	@curl -s http://localhost:3000 >/dev/null 2>&1 && echo "$(GREEN)✅ UI: Healthy$(RESET)" || echo "$(RED)❌ UI: Unhealthy$(RESET)"
	@echo ""

status: health ## Alias for health command

# Individual service commands
ui-only: ## Run only the UI
	@echo "$(YELLOW)Starting UI only...$(RESET)"
	cd ui && npm run dev &
	@sleep 3
	@echo "$(GREEN)🌐 UI available at: http://localhost:3000$(RESET)"
	@wait

runtime-only: ## Run only the Runtime API
	@echo "$(YELLOW)Starting Runtime API only...$(RESET)"
	@python -c "from database import init_db_sync; init_db_sync()" || echo "Database already initialized"
	python main.py --service runtime &
	@sleep 3
	@echo "$(GREEN)🔧 Runtime API available at: http://localhost:5003$(RESET)"
	@wait

mcp-only: ## Run only the MCP Server
	@echo "$(YELLOW)Starting MCP Server only...$(RESET)"
	python main.py --service mcp &
	@sleep 3
	@echo "$(GREEN)🧮 MCP Server available at: http://localhost:5005$(RESET)"
	@wait

# Quick setup commands
quick-start: install-all ## Install dependencies and start all services
	@echo "$(GREEN)🎉 Setup complete! Starting services...$(RESET)"
	@echo "$(CYAN)Run 'make dev' to start all services$(RESET)"
	@echo "$(CYAN)Or run 'make dev' now to start immediately$(RESET)"

demo: ## Run a quick demo
	@echo "$(CYAN)Running demo...$(RESET)"
	@echo "$(YELLOW)Testing Hello Agent...$(RESET)"
	@curl -X POST http://localhost:5001/api/message \
		-H "Content-Type: application/json" \
		-d '{"content": "Say hello in Spanish", "senderId": "demo"}' | jq '.content' 2>/dev/null || echo "Hello Agent not available"
	@echo ""
	@echo "$(YELLOW)Testing Math Agent...$(RESET)"
	@curl -X POST http://localhost:5004/api/message \
		-H "Content-Type: application/json" \
		-d '{"content": "What is 5 + 3?", "senderId": "demo"}' | jq '.content' 2>/dev/null || echo "Math Agent not available"
	@echo ""
	@echo "$(GREEN)Demo complete!$(RESET)"

# Environment checks
check-env: ## Check environment setup
	@echo "$(CYAN)Checking environment...$(RESET)"
	@python --version || echo "$(RED)❌ Python not found$(RESET)"
	@node --version 2>/dev/null && echo "$(GREEN)✅ Node.js available$(RESET)" || echo "$(YELLOW)⚠️  Node.js not found (needed for UI)$(RESET)"
	@docker --version 2>/dev/null && echo "$(GREEN)✅ Docker available$(RESET)" || echo "$(YELLOW)⚠️  Docker not found (optional)$(RESET)"
	@dotnet --version 2>/dev/null && echo "$(GREEN)✅ .NET available$(RESET)" || echo "$(YELLOW)⚠️  .NET not found (needed for Goodbye Agent)$(RESET)"
	@test -f .env && echo "$(GREEN)✅ .env file found$(RESET)" || echo "$(RED)❌ .env file missing$(RESET)"
	@echo ""

# Development helpers
watch: ## Watch for file changes and restart (requires entr)
	@echo "$(YELLOW)Watching for changes... (requires 'entr' command)$(RESET)"
	@find . -name "*.py" | entr -r make dev

format: ## Format Python code
	@echo "$(YELLOW)Formatting Python code...$(RESET)"
	@black . 2>/dev/null || echo "Install black: pip install black"
	@isort . 2>/dev/null || echo "Install isort: pip install isort"
	@echo "$(GREEN)✅ Code formatted$(RESET)"

# Quick access URLs
urls: ## Show all service URLs
	@echo "$(GREEN)🌐 Service URLs:$(RESET)"
	@echo "$(CYAN)UI:          http://localhost:3000$(RESET)"
	@echo "$(CYAN)Runtime API: http://localhost:5003$(RESET)"
	@echo "$(CYAN)Hello Agent: http://localhost:5001$(RESET)"
	@echo "$(CYAN)Goodbye Agent: http://localhost:5002$(RESET)"
	@echo "$(CYAN)Math Agent:  http://localhost:5004$(RESET)"
	@echo "$(CYAN)MCP Server:  http://localhost:5005$(RESET)"
	@echo ""
	@echo "$(GREEN)📚 API Documentation:$(RESET)"
	@echo "$(CYAN)Runtime API: http://localhost:5003/docs$(RESET)"
	@echo ""

# First time setup
first-run: check-env install-all ## Complete first-time setup
	@echo "$(GREEN)🎉 Setup complete! Ready to run:$(RESET)"
	@echo "$(CYAN)  make dev     # Start all services$(RESET)"
	@echo "$(CYAN)  make health  # Check service status$(RESET)"
	@echo "$(CYAN)  make urls    # Show all URLs$(RESET)"
	@echo ""