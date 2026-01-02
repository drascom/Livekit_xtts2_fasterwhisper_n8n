# Use a Python image (may need a non-slim image if specific TTS libs require system dependencies)
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies including curl for healthcheck and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Rust for building dependencies like sudachipy
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Copy dependency files and install them
COPY requirements.txt .
# TTS libraries can be complex, may require system packages or different base image.
# Using a base image that includes common audio libs is often a good start.
# If issues arise, a full Python image or a customized build will be needed.
RUN pip install --upgrade pip && \
    . "/root/.cargo/env" && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the application port
ENV PORT=8003
EXPOSE $PORT

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]