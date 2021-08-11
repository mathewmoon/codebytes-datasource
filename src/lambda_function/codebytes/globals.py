#!/usr/bin/env python3.8
from datetime import datetime
from os import environ
from boto3 import resource, client

TABLE_NAME = environ.get("TABLE")
TABLE = resource("dynamodb").Table(TABLE_NAME)
LAMBDA = client("lambda")
DEFAULT_LAMBDA_TIMEOUT = int(environ.get("DEFAULT_LAMBDA_TIMEOUT", "3"))
FREE_SNIPPET_TTL_HOURS = int(environ.get("FREE_SNIPPET_TTL_HOURS", "24"))
APP_URL = environ["APP_URL"]
SYSTEM_USER = "SYSTEM"


def isotime():
    return datetime.now().isoformat()


def get_user():
    return SYSTEM_USER