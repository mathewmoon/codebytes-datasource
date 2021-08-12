#!/usr/bin/env python3.8
from codebytes.runtimes import SharedSnippet, Snippet

"""
shared = SharedSnippet(
    user="mathewmoon",
    owner="mathewmoon",
    read=True,
    write=True,
    name="foo"
)
"""
# print(shared.user)

# snip = Snippet(
#     name="test sharing",
#     code="print('shared snippet')",
#     user="mathewmoon",
#     runtime="python38",
#     permissions=[{"user": "some_user", "read": True, "write": True}],
#     public=False
# )
# snip.create()

shared = SharedSnippet.get_item(name="test sharing", owner="mathewmoon", user="some_user")
print(shared.exec())
#print(shared.exec())

# print(snip.create())
