#!/usr/bin/env python3.8
import codebytes
from resolvers import router, logger
logger.setLevel("DEBUG")


def handler(event, _):
    logger.debug(event)
    codebytes.globals.USER = event["identity"].get("claims", {}).get("email") or codebytes.globals.SYSTEM
    res = router.resolve(event)
    logger.debug(f"RESULT: {res.value}")

    return res
