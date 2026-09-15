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
# #2096 : env renommée projet-is (environment.yml:1) — projet-is-v2 n'existe plus
SHELL ["conda", "run", "-n", "projet-is", "/bin/bash", "-c"]

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install project in editable mode
RUN pip install -e .

RUN pip install jpype1
RUN pip install mcp

# Command to run the MCP server
# #2096 : chemin racine pré-migration #34 — le module vit sous
# argumentation_analysis/services/mcp_server/ depuis la consolidation
CMD ["conda", "run", "--no-capture-output", "-n", "projet-is", "python", "argumentation_analysis/services/mcp_server/main.py"]
