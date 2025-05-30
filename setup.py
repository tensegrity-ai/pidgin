from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="pidgin",
    version="0.1.0",
    author="Pidgin Research Team",
    description="AI Communication Protocol Research CLI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/pidgin",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.9",
    install_requires=[
        "typer>=0.9.0",
        "rich>=13.0.0",
        "anthropic>=0.21.0",
        "openai>=1.12.0",
        "google-generativeai>=0.4.0",
        "pydantic>=2.0.0",
        "pydantic-settings>=2.0.0",
        "pyyaml>=6.0",
        "aiosqlite>=0.19.0",
        "sqlalchemy>=2.0.0",
        "numpy>=1.24.0",
        "python-dotenv>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "pidgin=pidgin.cli:app",
        ],
    },
)