#!/usr/bin/env python3.8
from typing import (
    NamedTuple,
    List
)
from json import dumps, loads
from time import time
from uuid import uuid4
from globals import (
    TABLE,
    LAMBDA,
    DEFAULT_LAMBDA_TIMEOUT,
    FREE_SNIPPET_TTL_HOURS,
    APP_URL,
    SYSTEM_USER,
    isotime
)
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr


class CodeBytes:
    _identifier = None
    required = set()
    __immutable = {
        "pk",
        "sk",
        "gsi0_pk",
        "gsi1_pk",
        "user",
        "name",
        "email",
        "TTL",
        "createdAt",
        "__typename"
    }
    __required = {
        "pk",
        "sk",
        "name",
        "user",
        "createdAt",
        "updatedAt"
    }

    def __new__(cls, *args, user=SYSTEM_USER, **kwargs):
        cls.__immutable |= cls.immutable
        cls.__required |= cls.required
        cls.__indexes = cls._indexes
        cls.all_keys = set()
        cls.all_keys |= cls.__immutable
        cls.all_keys |= cls.__required
        cls.all_keys |= cls.optional
        cls.all_keys |= set(cls.__indexes.values())
        cls.item = {}
        instance = super().__new__(cls)
        return instance

    def __init__(self, *args, **kwargs):
        for k, v in kwargs.items():
            if v is not None:
                setattr(self, k, v)

        for k, v in kwargs.items():
            if k in self.all_keys and v is not None:
                self.item[k] = v

    def __setattr__(self, name, value) -> None:
        if name in self.all_keys and value is not None:
            self.item[name] = value
        if value and name in self.__indexes:
            index_name = self.__indexes[name]
            self.item[index_name] = value
            super().__setattr__(index_name, value)

        super().__setattr__(name, value)

    @classmethod
    def get(
        cls,
        name: str,
        user: str,
        as_dict: bool = False
    ):
        user = user or "SYSTEM"
        sk = f"{cls._identifier}~{name}"
        item = TABLE.get_item(
            Key={
                "pk": user,
                "sk": sk
            }
        ).get("Item", {})

        if as_dict:
            return item
        else:
            return cls(**item)

    def get_time(self, op="createdAt"):
        return {
            op: isotime(),
            "by": self.user
        }

    def validate_keys(self):
        keys = list(self.item.keys())
        for x in self.__required:
            if x not in keys:
                raise Exception(f"Missing value for required attribute '{x}'")

    def create(self):
        self.pk = self.user or "SYSTEM"
        self.sk = f"{self._identifier}~{self.item['name']}"
        self.__typename = self._identifier.title()
        self.createdAt = self.get_time(op="createdAt")
        self.updatedAt = self.get_time(op="updatedAt")
        self.validate_keys()
        try:
            TABLE.put_item(
                Item=self.item,
                ConditionExpression=Attr("pk").not_exists() & Attr("sk").not_exists()
            )
            return self
        except ClientError as e:
            if e.response['Error']['Code'] != 'ConditionalCheckFailedException':
                raise Exception("Item already exists. Create a new item or use update")
            else:
                raise e

    def update(self, item):
        self.updatedAt = self.get_time(op="updatedAt")
        for k, v in item.items():
            if k in self.__immutable and v != self.__getattribute__(k):
                raise Exception(f"Not allowed to change value for '{k}'")
            else:
                setattr(self, k, v)

        self.validate_keys(update=True)

        try:
            TABLE.put_item(
                Item=item,
                ConditionExpression=Attr("system").ne(True)
            )
            return self
        except ClientError as e:
            if e.response['Error']['Code'] != 'ConditionalCheckFailedException':
                raise Exception(
                    "Cannot update builtin items")
            else:
                raise e

    def dict(self):
        return self.item


class Runtime(CodeBytes):
    _identifier = "RUNTIME"
    _indexes = {}
    executor = None
    __client = LAMBDA
    immutable = {
        "name",
        "user",
        "system",
        "requirements",
        "arn"
    }
    optional = {
        "description"
    }
    required = {
        "name"
    }

    def __new__(
        cls,
        *args,
        **kwargs
    ):
        instance = super().__new__(cls, *args, **kwargs)
        return instance

    def __init__(
        self,
        name: str,
        user: str = None,
        requirements: List[str] = [],
        **kwargs
    ):
        super().__init__(
            name=name,
            user=user,
            requirements=requirements,
            **kwargs
        )

    def execute(self, code, timeout=DEFAULT_LAMBDA_TIMEOUT):
        payload = dumps({
            "code": code,
            "timeout": timeout
        }).encode()
        res = self.__client.invoke(
            FunctionName=self.arn,
            InvocationType="RequestResponse",
            Payload=payload
        )
        result = loads(res["Payload"].read().decode())
        return result


class Snippet(CodeBytes):

    _identifier = "SNIPPET"
    _indexes = {
        "rw_url": "gsi1_sk",
        "ro_url": "gsi0_sk"
    }
    required = {
        "code",
        "public",
        "permissions",
        "runtime"
    }
    optional = {
        "description",
    }
    immutable = {
        "runtime",
        "rw_url",
        "ro_url"
    }

    def __new__(cls, *args, **kwargs):
        instance = super().__new__(cls, *args, **kwargs)
        return instance

    def __init__(
        self,
        runtime: str,
        code: str,
        user: str = SYSTEM_USER,
        name: str = None,
        public: bool = True,
        description: str = "",
        permissions: List[dict] = [],
    ):

        super().__init__(
            self,
            name=name,
            runtime=runtime,
            code=code,
            user=user,
            public=public,
            description=description,
            permissions=permissions
        )
        self.executor = Runtime.get(runtime, user)

    def create(self):
        if not self.user or self.user == SYSTEM_USER:
            self.public = True
            user_url_var = "public"
            self.TTL = self.get_ttl()
            self.name = uuid4().hex
        else:
            user_url_var = self.user

        url = f"{APP_URL}/snippets/{user_url_var}/{self.name}"
        self.ro_url = f"{url}/get"
        self.rw_url = f"{url}/edit"

        return super().create()

    def get_ttl(self):
        return int(time()) + (FREE_SNIPPET_TTL_HOURS * 3600)

    def exec(self):
        return self.executor.execute(self.code)


snippet = Snippet(code="print('called func')", runtime="python38")
print(snippet)
print(snippet.create().dict())
print(snippet.exec())