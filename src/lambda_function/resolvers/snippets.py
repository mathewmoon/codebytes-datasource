#!/usr/bin/env python3.8
from resolvers import router
from codebytes.snippets import Snippet
from codebytes.globals import get_user


@router.route(path="Snippet.Create")
def create_snippet():
    snippet = Snippet(
        **router.arguments,
        user=get_user()
    )
    if res := snippet.create():
        return res.item()


@router.route(path="Snippet.Create")
def update_snippet():
    name = router.arguments["name"]
    if snippet := Snippet.get(
        name=name,
        user=get_user
    ):
        return snippet.update(router.arguments).dict()
    else:
        raise Exception(f"Snippet {name} does not exist. Use create to make it")


@router.route(path="Snippet.Execute")
def execute_snippet():
    name = router.arguments["name"]
    if snippet := Snippet.get(
        name=name,
        user=get_user()
    ):
        return snippet.exec()
    else:
        raise Exception("Snippet {name} does not exist")


@router.route(path="Snippet.Get")
def get_snippet():
    name = router.arguments["name"]
    if snippet := Snippet.get(
        name=name,
        user=get_user(),
        as_dict=True
    ):
        return snippet
    else:
        raise Exception("Snippet {name} does not exist")
