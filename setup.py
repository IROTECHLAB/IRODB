import os
import re
from setuptools import setup, find_packages

# Read version from __init__.py
with open("irodb/__init__.py", "r", encoding="utf-8") as f:
    version_match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', f.read())
    version = version_match.group(1) if version_match else "0.1.0"

# Read README
try:
    with open("README.md", "r", encoding="utf-8") as fh:
        long_description = fh.read()
        print(f"✅ README.md loaded: {len(long_description)} characters")
except FileNotFoundError:
    long_description = "IRODB - A Python database library with .irodb format and hash-based indexing"
    print("❌ README.md not found")

setup(
    name="irotechlab_irodb",
    version=version,
    author="IroTechLab",
    author_email="",  # Fixed: Added comma
    description="A Python database library with .irodb format and hash-based indexing",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/IrotechLab/irodb",
    project_urls={
        "Bug Tracker": "https://github.com/IrotechLab/irodb/issues",
        "Source Code": "https://github.com/IrotechLab/irodb",
        "Telegram": "https://t.me/ironmanhindigaming",
        "Documentation": "https://github.com/IroTechLab/irodb#readme",
    },
    packages=find_packages(include=['irodb', 'irodb.*']),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Database",
        "Topic :: Database :: Database Engines/Servers",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.6",
    install_requires=[],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "irodb=irodb.cli:main",
        ],
    },
    keywords="database, db, nosql, hash, indexing, integrity, irodb",
    license="MIT",
    include_package_data=True,
    zip_safe=False,
)
