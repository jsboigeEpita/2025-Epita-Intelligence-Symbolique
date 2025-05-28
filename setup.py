from setuptools import setup, find_packages

setup(
    name="argumentation_analysis",
    version="0.1.0",
    packages=find_packages() + ['services', 'services.web_api'],
    package_dir={'services': 'services'},
    install_requires=[
        "semantic-kernel",
        "pytest",
        "pytest-cov",
        "pandas",
        "numpy",
        "matplotlib",
        "jpype1",
        "cryptography",
        "seaborn",
        "tqdm",
    ],
    python_requires=">=3.8",
    description="Système d'analyse argumentative",
    author="EPITA",
    author_email="contact@epita.fr",
)