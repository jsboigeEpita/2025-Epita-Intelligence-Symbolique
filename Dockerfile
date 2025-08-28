# Stage 1: Builder
FROM continuumio/miniconda3 AS builder

# Définir les variables d'environnement
ENV PYTHONUNBUFFERED=1

# Copier le fichier de dépendances
COPY environment.yml .

# Installer les dépendances
RUN conda env update --file environment.yml --prune

# Stage 2: Runtime
FROM continuumio/miniconda3

# Copier l'environnement depuis le builder
COPY --from=builder /opt/conda/ /opt/conda/

# Définir le répertoire de travail
WORKDIR /app

# Copier le code source
COPY . .

# Définir le point d'entrée
CMD ["python", "-c", "print('Application containerisée démarrée avec succès.')"]