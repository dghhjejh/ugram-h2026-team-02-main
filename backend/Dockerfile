# Use standard Python image
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
RUN uv sync --no-dev --no-install-project

# Copy the rest of the application
COPY . /app/

# Install the project itself and sync again
RUN uv sync --no-dev

# Place the virtual environment in the path
ENV PATH="/app/.venv/bin:$PATH"

# Document the container port for local runs and EB.
EXPOSE 8001

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001"]
