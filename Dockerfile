# Use standard Python image to avoid ghcr.io auth issues
FROM python:3.13-slim

# Install uv
RUN pip install uv

# Set the working directory to /app
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy the lockfile and pyproject.toml separately for better cache invalidation
COPY uv.lock pyproject.toml /app/

# Install dependencies
RUN uv sync --frozen --no-install-project

# Copy the rest of the application
COPY . /app/

# Install the project itself and sync again
RUN uv sync --frozen

# Place the virtual environment in the path
ENV PATH="/app/.venv/bin:$PATH"

# Run the application
CMD ["python", "-m", "src.main"]
