#!/usr/bin/env python3.8
from codebytes.globals import Globals
from resolvers import router, logger
logger.setLevel("DEBUG")

GLOBALS = Globals()


def handler(event, _):
    logger.debug(event)

    set_user(event["identity"])
    res = router.resolve(event)
    logger.debug(f"RESULT: {res.value}")

    return res


def set_user(identity):
    global GLOBALS
    claims = identity.get("claims", {})
    if user := claims.get("email"):
        GLOBALS.user = user
    else:
        GLOBALS.user = GLOBALS.SYSTEM_USER

    return GLOBALS.user