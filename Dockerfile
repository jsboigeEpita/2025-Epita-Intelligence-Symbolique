# Multi-stage Dockerfile for Argumentation Analysis System
# Reproducibility package — soutenance verification
#
# Build:  docker build -t arg-analysis .
# Run:    docker compose up demo
# Verify: docker compose run demo scripts/repro/run_demo.sh

# ---- Stage 1: Build dependencies ----
FROM continuumio/miniconda3:latest AS builder

WORKDIR /build

COPY environment.yml .

RUN conda env create -f environment.yml -n projet-is && \
    conda clean -afy

# ---- Stage 2: Runtime ----
FROM continuumio/miniconda3:latest

LABEL maintainer="Equipe Projet IS"
LABEL description="Multi-agent argumentation analysis system — EPITA reproducibility package"

# Install JDK 17 (Temurin) for Tweety/JPype
RUN apt-get update && \
    apt-get install -y --no-install-recommends wget gnupg2 && \
    wget -O - https://packages.adoptium.net/artifactory/api/gpg/key/public | apt-key add - && \
    echo "deb https://packages.adoptium.net/artifactory/deb $(grep VERSION_CODENAME /etc/os-release | cut -d= -f2) main" \
        > /etc/apt/sources.list.d/adoptium.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends temurin-17-jdk && \
    apt-get purge -y wget gnupg2 && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/temurin-17-jdk-amd64

# Copy conda environment from builder
COPY --from=builder /opt/conda/envs/projet-is /opt/conda/envs/projet-is

ENV CONDA_DEFAULT_ENV=projet-is
ENV PATH="/opt/conda/envs/projet-is/bin:${PATH}"
ENV PYTHONPATH="/app:/app/argumentation_analysis:/app/project_core"

WORKDIR /app

# Copy project files (respect .dockerignore)
COPY argumentation_analysis/ argumentation_analysis/
COPY project_core/ project_core/
COPY api/ api/
COPY examples/ examples/
COPY scripts/repro/ scripts/repro/
COPY pyproject.toml pytest.ini ./
COPY libs/ libs/

# Placeholder .env (API keys injected at runtime)
RUN printf "# API keys — inject via docker compose env-file or -e\nOPENAI_API_KEY=\nOPENAI_CHAT_MODEL_ID=gpt-5-mini\n" > .env

EXPOSE 8000

CMD ["python", "-c", "print('Use: docker compose up demo | api | verify')"]
