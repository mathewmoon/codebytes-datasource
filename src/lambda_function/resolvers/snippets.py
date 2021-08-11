#!/usr/bin/env python3.8
from resolvers import router
from codebytes.runtimes import Snippet
from codebytes.globals import Globals


@router.route(path="Snippet.Create")
def create_snippet():
    snippet = Snippet(
        **router.arguments
    )
    if res := snippet.create():
        return res.item


@router.route(path="Snippet.Update")
def update_snippet():
    name = router.arguments["name"]
    if snippet := Snippet.get(
        name=name
    ):
        return snippet.update(router.arguments).dict()
    else:
        raise Exception(f"Snippet {name} does not exist. Use create to make it")


@router.route(path="Snippet.Execute")
def execute_snippet():
    name = router.arguments["name"]
    if snippet := Snippet.get(
        name=name
    ):
        return snippet.exec()
    else:
        raise Exception("Snippet {name} does not exist")


@router.route(path="Snippet.Get")
def get_snippet():
    name = router.arguments["name"]
    if snippet := Snippet.get(
        name=name,
        as_dict=True
    ):
        return snippet
    else:
        raise Exception("Snippet {name} does not exist")
