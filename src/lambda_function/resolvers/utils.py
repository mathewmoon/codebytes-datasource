#!/usr/bin/env python3.8
from boto3 import resource
from os import environ

TABLE_NAME = environ.get("TABLE")
TABLE = resource("dynamodb").Table(TABLE_NAME)

