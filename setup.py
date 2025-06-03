from setuptools import setup, find_packages

setup(
    name="argumentation_analysis",
    version="0.1.0",
    packages=find_packages(exclude=["tests", "scripts", "docs", "notebooks", "venv", ".venv", "dist", "build", "*.egg-info"]),
    # package_dir={'': 'src'},
    install_requires=[
        "numpy>=2.0.0,<2.3",  # Ajusté pour thinc et scipy
        "pandas",
        "scipy==1.13.1",
        "scikit-learn",
        "nltk",
        # "spacy==3.8.7", # Temporairement retiré
        # "thinc==8.2.3",
        # "blis==0.7.11",
        # "srsly==2.5.1",
        # "preshed==3.0.10",
        # "murmurhash==1.0.13",
        # "cymem==2.0.11",
        "torch",
        "transformers",
        "pydantic>=2.0,<2.10",
        "requests",
        "matplotlib",
        "seaborn",
        "networkx==3.2.1",
        "python-dotenv",  # Pour l'import de 'dotenv'
        "semantic-kernel~=0.9.7b1", # Tentative de mise à jour mineure pour AuthorRole
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
    ],
    python_requires=">=3.8",
    description="Système d'analyse argumentative",
    author="EPITA",
    author_email="contact@epita.fr",
)