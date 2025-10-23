from shutil import which
from subprocess import run
from time import perf_counter

import toml
import ujson
from humanize import naturaldelta
from rich.console import Console

start_time = perf_counter()
pprint = Console().print
page = """
---
title: Keybindings
description: A reference for all default keybindings in rovr.
---

this page provides a comprehensive list of the default keybindings in `rovr`. you can customize these keybindings in your `config.toml` file.

| action | default hotkey | description |
| ------ | -------------- | ----------- |"""
try:
    with open("src/rovr/config/config.toml", "r", encoding="utf-8") as file:
        binds: dict = toml.load(file)["keybinds"]
    with open("src/rovr/config/schema.json", "r", encoding="utf-8") as file:
        schema: dict = ujson.load(file)["properties"]["keybinds"]["properties"]
    for key, values in schema.items():
        to_add = "\n| "
        to_add += key
        to_add += " |"
        for bind in binds[key]:
            to_add += f" <kbd>{bind}</kbd>"
        to_add += " | "
        to_add += values["display_name"]
        to_add += " |"
        page += to_add
    with open(
        "docs/src/content/docs/reference/keybindings.mdx", "w", encoding="utf-8"
    ) as file:
        file.write(page)
    # attempt to format it
    if which("prettier"):
        run(
            ["prettier", "--write", "docs/src/content/docs/reference/keybindings.mdx"],
            shell=True,
        )
    elif which("npx"):
        run(
            [
                "npx",
                "prettier",
                "--write",
                "docs/src/content/docs/reference/keybindings.mdx",
            ],
            shell=True,
        )
    else:
        pprint(
            "[red][blue]prettier[/] and [blue]npx[/] are not available on PATH, and hence the generated files cannot be formatted."
        )
        exit(1)
    pprint(
        f"[green]Generated it in {naturaldelta(perf_counter() - start_time, minimum_unit='microseconds')}"
    )
except FileNotFoundError:
    pprint("[red]Do not run manually with python! Run [blue]poe gen-keys[/][/]")
    exit(1)
