#!/usr/bin/env python3.8
from datetime import datetime
from threading import RLock
from os import environ
from boto3 import resource, client


class Globals:
    TABLE_NAME = environ.get("TABLE")
    TABLE = resource("dynamodb").Table(TABLE_NAME)
    LAMBDA = client("lambda")
    DEFAULT_LAMBDA_TIMEOUT = int(environ.get("DEFAULT_LAMBDA_TIMEOUT", "3"))
    FREE_SNIPPET_TTL_HOURS = int(environ.get("FREE_SNIPPET_TTL_HOURS", "24"))
    APP_URL = environ["APP_URL"]
    SYSTEM_USER = "SYSTEM"
    ANONYMOUS_USER = "ANONYMOUS"
    __instance = None
    __initialized = None
    __user = None

    def __new__(cls):
        if not cls.__instance:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    @property
    def user(self):
        return self.__user

    @user.setter
    def user(self, value):
        print("Changed user")
        self.__user = value


def isotime():
    return datetime.now().isoformat()
