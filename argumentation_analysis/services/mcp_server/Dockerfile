# Use official Python image as base
FROM python:3.10-slim

# Install conda for ARM64
RUN apt-get update && apt-get install -y wget && \
    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-aarch64.sh -O miniconda.sh && \
    bash miniconda.sh -b -p /opt/conda && \
    rm miniconda.sh

# Add conda to path
ENV PATH="/opt/conda/bin:${PATH}"

# Create conda environment
COPY environment.yml .
RUN conda env create -f environment.yml

# Make RUN commands use the new environment
SHELL ["conda", "run", "-n", "projet-is-v2", "/bin/bash", "-c"]

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install project in editable mode
RUN pip install -e .

RUN pip install jpype1
RUN pip install mcp

# Command to run the MCP server
CMD ["conda", "run", "--no-capture-output", "-n", "projet-is-v2", "python", "services/mcp_server/main.py"]
