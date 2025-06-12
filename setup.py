from setuptools import setup, find_packages

setup(
    name="argumentation-analysis-project",
    version="0.1.0",
    packages=find_packages(
        where='.',
        include=['argumentation_analysis*', 'speech_to_text*', 'project_core*', 'scripts*'],
        exclude=['tests', 'tests.*']
    ),
    python_requires=">=3.8",
)