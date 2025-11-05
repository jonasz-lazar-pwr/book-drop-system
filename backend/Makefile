.PHONY: format lint test check clean

# Auto-fix & format
format:
	ruff format .

# Linting (analysis with auto fix)
lint:
	ruff check .

# Run tests with coverage
test:
	@bash -c 'export $$(grep -vE "^(#|$$)" .env.test | xargs) && pytest --cov=api --cov=core --cov=models --cov=schemas --cov=services --cov-report=term-missing'

# Run everything (lint + tests)
check: format lint test

# Clean up cache and artifacts
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache .coverage coverage.xml