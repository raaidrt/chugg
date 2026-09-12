"""Finite UI states and the action names exchanged with the browser host."""

from typing import Literal, TypeIs, get_args

type Page = Literal["practice", "library", "progress"]
type Dialog = Literal["menu", "settings", "sampling", "install", "moves"]
type Platform = Literal["iphone", "android"]
type SettingsAction = Literal["export", "import", "persist"]

# Keep this literal flat so the browser boundary can validate it at runtime.
type Action = Literal[
    "practice",
    "library",
    "progress",
    "start",
    "replay",
    "square",
    "hint",
    "promote",
    "cancel-promotion",
    "menu",
    "settings",
    "sampling",
    "install",
    "moves",
    "close",
    "search",
    "family",
    "clear-filters",
    "platform",
    "dismiss",
    "offline",
    "online",
    "export",
    "import",
    "persist",
    "file-error",
    "update",
]

# The host handles the file-picker action without dispatching it to Python.
type ButtonAction = Action | Literal["choose-backup"]


def is_action(value: str) -> TypeIs[Action]:
    return value in get_args(Action.__value__)
