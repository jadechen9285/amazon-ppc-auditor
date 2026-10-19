FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Install uv (The official recommended installation method for Docker)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy your dependency files first to leverage Docker layer caching
COPY pyproject.toml uv.lock* ./

# Sync runtime dependencies only (dev tooling is excluded from the image)
RUN uv sync --frozen --no-dev --no-install-project

# 2. Application Layer (Explicitly whitelist only the necessary source code)
COPY src/ ./src/
COPY dashboards/ ./dashboards/
COPY .streamlit/ ./.streamlit/

# Make the src/ packages (backend, ui) importable by the Streamlit entrypoint
ENV PYTHONPATH=/app/src

# Expose the default Streamlit port
EXPOSE 8501

# Execute the app using 'uv run' to automatically target the generated virtual environment
CMD ["uv", "run", "--no-sync", "streamlit", "run", "dashboards/ppc_audit_report.py", "--server.port=8501", "--server.address=0.0.0.0"]