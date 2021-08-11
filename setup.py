#!/usr/bin/env python3.8
from setuptools import setup, find_packages

lambda_name = "appsync-resolver"

lambda_version = "0.0.1"

lambda_description = "Appsync resolver Lambda"

long_description = lambda_description

lambda_dev_status = "3 - Alpha"

lambda_keywords = "lambda"

lambda_license = "Proprietary"

lambda_author = ""
lambda_author_email = ""

lambda_install_requires = ["setuptools"]
lambda_python_version = ">=3.8"

setup(
    name=lambda_name,
    version=lambda_version,
    description=lambda_description,
    long_description=long_description,
    author=lambda_author,
    author_email=lambda_author_email,
    # Choose your license
    license=lambda_license,
    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        "Development Status :: " + lambda_dev_status,
        # Pick your license as you wish (should match "license" above)
        "License :: " + lambda_license,
        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        "Programming Language :: Python :: " + lambda_python_version,
    ],
    keywords=lambda_keywords,
    install_requires=[
        x for x in lambda_install_requires if x not in ["boto3", "botocore"]
    ],
    package_dir={"": "src"},
    packages=find_packages("src"),
    include_package_data=True,
    lambda_package="src/lambda_function",
    setup_requires=["lambda-setuptools"],
)
