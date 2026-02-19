.PHONY: help install conformance test test-unit scan docker-build docker-run clean

PYTHON ?= python3
PIP ?= pip3

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
	@echo ""

install: ## Install OSP SDK and all dependencies
	$(PIP) install -e '.[full]'
	$(PIP) install -e osp_core/

conformance: install ## Run OSP conformance test suite (CONF-01)
	@echo "\033[95m⚡ OSP Conformance Suite\033[0m"
	$(PYTHON) tests/conformance_harness.py
	@echo "\033[92m✅ Conformance tests complete\033[0m"

test: install ## Run all tests (unit + integration)
	@echo "\033[95m⚡ Full OSP Test Suite\033[0m"
	$(PYTHON) -m pytest tests/ -v --tb=short
	@echo "\033[92m✅ Tests complete\033[0m"

test-unit: ## Run unit tests only (fast)
	$(PYTHON) -m pytest tests/ -v --tb=short -k "not e2e"

scan: ## Scan for leaked secrets / developer paths
	@echo "\033[93m🔍 Scanning for secrets...\033[0m"
	@! grep -rn "39l90kv\|GOCSPX\|b8844f8c\|oleksandrosadchiy\|api_id = [0-9]" \
		--include="*.py" --include="*.md" --include="*.json" --include="*.yaml" \
		--exclude-dir=".git" . \
		&& echo "\033[92m✅ No secrets found\033[0m" \
		|| (echo "\033[91m❌ Secrets detected — see above\033[0m" && exit 1)

docker-build: ## Build the OSP Docker image
	docker build -t osp-sdk:latest .

docker-run: ## Run the OSP server in Docker (requires OSP_ADMIN_KEY)
	docker run --rm \
		-e OSP_ADMIN_KEY=$${OSP_ADMIN_KEY:-changeme} \
		-e OSP_CORS_ORIGINS=$${OSP_CORS_ORIGINS:-http://localhost:8080} \
		-p 8000:8000 \
		osp-sdk:latest

clean: ## Remove Python cache files
	find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
	find . -name '*.pyc' -delete 2>/dev/null || true
