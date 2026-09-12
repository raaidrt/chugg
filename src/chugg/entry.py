"""Pyodide entry point; native tooling never imports browser-only modules."""

from js import chuggHost  # pyright: ignore[reportMissingModuleSource]
from pyodide.ffi import create_proxy  # pyright: ignore[reportMissingModuleSource]

from chugg.app import App

app = App(chuggHost, create_proxy)
app.spawn(app.initialize())
