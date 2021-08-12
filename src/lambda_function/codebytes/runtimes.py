#!/usr/bin/env python3.8
from typing import List
from collections import UserDict
from json_deserializer import dumps, loads
from time import time
from urllib.parse import quote_plus
from uuid import uuid4
from .globals import Globals, isotime
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr


class CodeBytes(UserDict):
    __indexes = {}

    def __init__(self, *args, **kwargs):
        if "user" not in kwargs:
            kwargs["user"] = Globals().user

        self.__immutable = {
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
        self.__required = {
            "pk",
            "sk",
            "name",
            "user",
            "createdAt",
            "updatedAt"
        }
        self.__indexes = self._indexes
        self.all_keys = set()
        self.__immutable |= self.immutable
        self.__required |= self.required
        self.all_keys |= self.__immutable
        self.all_keys |= self.__required
        self.all_keys |= self.optional
        self.all_keys |= set(self.__indexes.values())
        self.__typename = self._identifier.title()
        super().__init__(*args, **kwargs)
        for k, v in kwargs.items():
            if v is not None:
                setattr(self, k, v)

        for k, v in kwargs.items():
            if k in self.all_keys and v is not None:
                self[k] = v

    def __setitem__(self, key, value) -> None:
        if value and key in self.__indexes:
            index = self.__indexes[key]
            super().__setitem__(index, value)
        super().__setitem__(key, value)

    def __setattr__(self, name, value) -> None:
        if value and name in self.__indexes:
            index = self.__indexes[name]
            super().__setattr__(index, value)

        super().__setattr__(name, value)

    @classmethod
    def list_items(
        cls,
        key_condition,
        index=None,
        filter=None,
        start_key=None,
        user=None
    ):
        user = user or Globals().user
        opts = {
            "KeyCondtionExpression": key_condition,
        }
        if index:
            opts["Index"] = index

        if start_key:
            opts["ExclusiveStartKey"] = start_key

        if filter:
            opts["FilterExpression"] = filter

        res = Globals().TABLE.query(**opts)

        for x in res["Items"]:
            cls.check_permissions(x, "read", user)

        return {
            "results": res["Items"],
            "count": len(res["Items"]),
            "next": res.get("LastEvaluatedKey")
        }

    @classmethod
    def get_item(
        cls,
        name: str,
        user: str = None,
        skip_auth: bool = False,
        get_for=None
    ):
        user = user or Globals().user
        sk = f"{cls._identifier}~{name}"
        item = Globals().TABLE.get_item(
            Key={
                "pk": user,
                "sk": sk
            }
        ).get("Item", {})

        if not skip_auth:
            cls.check_permissions(item, "read", user=user, get_for=get_for)

        return cls(**item)

    @classmethod
    def check_permissions(cls, item, permission, user=None, get_for=None):
        user = get_for or user or Globals().user
        if item["user"] == user:
            return True

        permissions = {
            x["user"]: x
            for x in item.get("permissions", [])
        }

        if permissions.get(user, {}).get(permission) is True:
            return True

        if item.get("public") and permission == "read":
            return True

        if item["user"] == "PUBLIC_SNIPPETS" and permission == "read":
            return True

        if item["user"] == "PUBLIC_RUNTIMES" and permission == "read":
            return True

        raise Exception("Not authorized to get item")

    def get_time(self, op="createdAt"):
        return {
            op: isotime(),
            "by": self.user
        }

    def validate_keys(self):
        keys = list(self.keys())
        for x in self.__required:
            if x not in keys:
                raise Exception(f"Missing value for required attribute '{x}'")

    def create(self, user=None, error_on_exists=True):
        user = user or self.user
        self["sk"] = f"{self._identifier}~{self.name}"
        self["pk"] = user
        self["__typename"] = self._identifier.title()
        self["createdAt"] = self.get_time(op="createdAt")
        self["updatedAt"] = self.get_time(op="updatedAt")
        self.validate_keys()
        opts = {}
        if error_on_exists:
            opts["ConditionExpression"] = Attr("pk").not_exists() & Attr("sk").not_exists()
        opts["Item"] = dict(self)
        try:
            Globals().TABLE.put_item(**opts)
            self.on_create()
            return self
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                raise Exception("Item already exists. Create a new item or use update")
            else:
                raise e

    def update_item(self, item):
        self.updatedAt = self.get_time(op="updatedAt")
        for k, v in item.items():
            if k in self.__immutable and v != self.__getattribute__(k):
                raise Exception(f"Not allowed to change value for '{k}'")
            else:
                setattr(self, k, v)
        self.update(item)

        self.check_permissions(self.user, "write", item)

        self.validate_keys(update=True)

        try:
            Globals().TABLE.put_item(
                Item=dict(self),
                ConditionExpression=Attr("system").ne(True)
            )
            self.on_update(item)
            return self
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                raise Exception(
                    "Cannot update builtin items")
            else:
                raise e

    def delete_item(self, user=None):
        user = user or self.user
        sk = f"{self._identifier}~{self.name}"
        pk = user
        Globals().TABLE.delete_item(
            Key={
                "sk": sk,
                "pk": pk
            }
        )
        self.on_delete()

    def on_create(self):
        pass

    def on_update(self, item):
        return item

    def on_delete(self):
        pass


class Runtime(CodeBytes):
    _identifier = "RUNTIME"
    _indexes = {}
    executor = None
    __client = Globals().LAMBDA
    immutable = {
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

    def __init__(
        self,
        name: str,
        user: str = None,
        requirements: List[str] = [],
        **kwargs
    ):
        super().__init__(
            name=name,
            user=user or Globals().user,
            requirements=requirements,
            **kwargs
        )

    def execute(self, code, timeout=Globals().DEFAULT_LAMBDA_TIMEOUT):
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


class SharedSnippet(CodeBytes):
    _indexes = {}
    _identifier = "SHARED_SNIPPET"
    required = {
        "owner",
    }
    immutable = {
        "owner"
    }
    optional = set()

    def __init__(
        self,
        *,
        owner: str,
        name: str,
        user: str = None,
        **kwargs
    ):

        super().__init__(
            owner=owner,
            name=f"{owner}|{name}",
            user=user or Globals().user
        )

    @classmethod
    def get_item(cls, name: str, owner: str, user: str = None):
        user = user or Globals().user
        name = f"{owner}|{name}"
        return super().get_item(name=name, user=user)

    @property
    def snippet(self):
        name = self.name.split("|")[1]
        user = self.user or Globals().user
        snippet = Snippet.get_item(name=name, user=self.owner, get_for=user)
        snippet.exec = self.exec_snippet
        snippet.delete_item = self.delete_snippet
        snippet.update_item = self.update_snippet
        return snippet

    def exec(self):
        return self.exec_snippet()

    def update_snippet(self, item):
        return self.snippet.update_item(item, user=self.user)

    def delete_snippet(self, _):
        raise Exception("Cannot delete shared items")

    def exec_snippet(self):
        perms = {
            x["user"]: x
            for x in self.snippet.permissions
        }
        if not perms[self.user]["execute"]:
            raise Exception("Not allowed to execute")
        else:
            return self.snippet._executor.execute(self.snippet.code)


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

    def __init__(
        self,
        runtime: str,
        code: str,
        user: str = None,
        name: str = None,
        public: bool = True,
        description: str = "",
        permissions: List[SharedSnippet] = [],
        **kwargs
    ):
        if public:
            name = uuid4().hex

        if not name:
            raise Exception("Name cannot be empty")

        user = user or Globals().user

        if not user or user == Globals().ANONYMOUS_USER:
            public = True
            user_url_var = "public"
        else:
            user_url_var = user

        url = f"{Globals().APP_URL}/snippets/{user_url_var}/{quote_plus(name)}"
        ro_url = f"{url}/get"
        rw_url = f"{url}/edit"

        super().__init__(
            self,
            name=name,
            runtime=runtime,
            code=code,
            user=user or Globals().user,
            public=public,
            description=description,
            permissions=permissions,
            ro_url=ro_url,
            rw_url=rw_url
        )
        self.__executor = None

    @property
    def _executor(self):
        if self.__executor is None:
            self.__executor = Runtime.get_item(self.runtime, self.user, skip_auth=True)
        return self.__executor

    def create(self):
        if not self.user or self.user == Globals().ANONYMOUS_USER:
            self.public = True
            user_url_var = "public"
            self.TTL = self.get_ttl()
            self.name = uuid4().hex
        else:
            user_url_var = self.user

        url = f"{Globals().APP_URL}/snippets/{user_url_var}/{quote_plus(self.name)}"
        self.ro_url = f"{url}/get"
        self.rw_url = f"{url}/edit"

        res = super().create(error_on_exists=False)
        return res

    def update_item(self, item):
        res = super().update_item(item)
        # self.make_permissions_changes(item=item)
        return res

    def on_update(self, item):
        # Permissions weren't changed
        if not item.get("permissions"):
            return

        new_permissions = {
            x["user"]: x
            for x in item.get("permissions", [])
        }

        current_permissions = {
            x["user"]: x
            for x in self.permissions
        }

        for user, permission in current_permissions.items():
            if user not in new_permissions:
                SharedSnippet(**permission, owner=self.user).delete()
        for user, permission in new_permissions.items():
            if (
                user not in current_permissions
                or current_permissions[user] != permission
            ):
                SharedSnippet(**permission, owner=self.user).create(error_on_exists=False)

    def on_create(self):
        for item in self.permissions:
            snippet = SharedSnippet(**item, owner=self.user, name=self.name)
            snippet.create()

    def on_delete(self):
        for item in self.permissions:
            SharedSnippet(**item, owner=self.user).delete_item()

    def get_ttl(self):
        return int(time()) + (Globals().FREE_SNIPPET_TTL_HOURS * 3600)

    def exec(self, user: str = None):
        user = user or Globals().user
        return self._executor.execute(self.code)
