from setuptools import setup, find_packages

setup(
    name="argumentation_analysis",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "numpy<2.0",  # Contrainte cruciale pour la compatibilité
        "pandas",
        "scipy==1.15.3",
        "scikit-learn",
        "nltk",
        "spacy",
        "torch",
        "transformers",
        "pydantic>=2.0,<2.10",
        "requests",
        "matplotlib",
        "seaborn",
        "networkx==3.4.2",
        "python-dotenv",  # Pour l'import de 'dotenv'
        "semantic-kernel==1.29.0", # Version synchronisée
        "pytest",
        "pytest-cov",
        "pytest-mock",
        "pytest-asyncio",
        "coverage",
        "cryptography",
        "jpype1",
        "flask",
        "Flask-CORS",
        "tqdm",
    ],
    python_requires=">=3.8",
    description="Système d'analyse argumentative",
    author="EPITA",
    author_email="contact@epita.fr",
)