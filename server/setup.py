from setuptools import setup, find_packages
import os

# Read README.md
readme_path = os.path.join(os.path.dirname(__file__), "README.md")
if os.path.exists(readme_path):
    with open(readme_path, "r", encoding="utf-8") as fh:
        long_description = fh.read()
else:
    long_description = "A simulator for Neuro-Sama's streaming behavior"

# Read requirements.txt
requirements_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
if os.path.exists(requirements_path):
    with open(requirements_path, "r", encoding="utf-8") as fh:
        requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]
else:
    requirements = []

setup(
    name="neuro-simulator",
    version="0.0.2",  # Updated version
    author="Moha-Master",
    author_email="hongkongreporter@outlook.com",
    description="Neuro Simulator Server",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Moha-Master/neuro-simulator",
    packages=find_packages(include=['neuro_simulator', 'neuro_simulator.*'], exclude=['neuro_simulator.media']),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "neuro=neuro_simulator.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "neuro_simulator": ["settings.yaml.example", "media/*"],
    },
)