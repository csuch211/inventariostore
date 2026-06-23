default: check

# Run all tests
test:
    cd src && uv run pytest tests/ -v --tb=short

# Run linter
lint:
    uv run ruff check src/

# Auto-fix lint issues  
fix:
    uv run ruff check src/ --fix

# Format code
format:
    uv run ruff format src/

# Type-check (gradual)
typecheck:
    uv run mypy src/

# Run full quality gate
check: lint typecheck test

# Run the application
run:
    uv run flet run src/main.py

# Show coverage report
coverage:
    cd src && uv run pytest tests/ --cov --cov-report=term-missing
