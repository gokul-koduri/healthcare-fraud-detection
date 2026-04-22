"""
Setup script for Healthcare Claims Fraud Detection System
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="healthcare-fraud-detection",
    version="1.0.0",
    author="Healthcare Analytics Team",
    author_email="healthcare-analytics@company.com",
    description="Healthcare Claims Fraud Detection & Intelligent Audit Automation System",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourcompany/healthcare-fraud-detection",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Healthcare Industry",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.11",
    install_requires=[
        "pandas>=2.1.0",
        "numpy>=1.24.3",
        "scikit-learn>=1.3.0",
        "pyod>=1.1.2",
        "tensorflow>=2.13.0",
        "torch>=2.0.1",
        "pyspark>=3.4.0",
        "sqlalchemy>=2.0.20",
        "snowflake-connector-python>=3.2.0",
        "openai>=1.3.0",
        "langchain>=0.0.300",
        "boto3>=1.28.50",
        "matplotlib>=3.7.2",
        "seaborn>=0.12.2",
        "pyyaml>=6.0.1",
        "python-dotenv>=1.0.0",
        "loguru>=0.7.2",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.2",
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mlflow>=2.7.1",
        ],
        "dbt": [
            "dbt-core>=1.5.0",
            "dbt-snowflake>=1.5.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "hfd-train=src.train_models:main",
            "hfd-predict=src.predict_fraud:main",
            "hfd-pipeline=src.run_pipeline:main",
            "hfd-report=src.genai.generate_audit_report:main",
        ],
    },
)
