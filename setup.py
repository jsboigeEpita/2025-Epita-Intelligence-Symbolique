from setuptools import setup, find_packages

setup(
    name="argumentation_analysis_project",
    version="0.1.0",
    packages=find_packages(exclude=["tests", "tests.*", "scripts", "scripts.*", "docs", "docs.*", "notebooks", "notebooks.*", "venv", ".venv", "dist", "build", "*.egg-info", "_archives", "_archives.*", "examples", "examples.*", "config", "config.*", "services", "services.*", "tutorials", "tutorials.*", "libs", "libs.*", "results", "results.*", "src", "src.*"]),
    # package_dir={'': 'src'},
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
        "semantic-kernel==1.29.0", # Version qui contient le module agents/
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
        'markdown',
        "unidecode",
    ],
    python_requires=">=3.8",
    description="Système d'analyse argumentative",
    author="EPITA",
    author_email="contact@epita.fr",
)