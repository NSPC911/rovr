from shutil import which
from subprocess import CalledProcessError, run
from time import perf_counter

import tomli
import ujson
from humanize import precisedelta
from rich.console import Console
from rich.traceback import Traceback

start_time = perf_counter()
pprint = Console().print
page = """
---
title: Keybindings
description: A reference for all default keybindings in rovr.
---

this page provides a comprehensive list of the default keybindings in `rovr`. you can customize these keybindings in your `config.toml` file.

## main bindings

| action | default hotkey | description |
| ------ | -------------- | ----------- |"""
try:
    with open("src/rovr/config/config.toml", "rb") as file:
        binds: dict = tomli.load(file)["keybinds"]
    with open("src/rovr/config/schema.json", "r", encoding="utf-8") as file:
        sub_schema: dict = ujson.load(file)["properties"]["keybinds"]["properties"]
    sub_schemas: dict[str, dict] = {}
    sub_keys: dict[str, dict] = {}
    for key, values in sub_schema.items():
        if isinstance(binds[key], dict):
            sub_schemas[key] = values
            sub_keys[key] = binds[key]
            continue
        elif isinstance(binds[key], str):
            binds[key] = [binds[key]]
        to_add = f"\n| {key} |"
        for bind in binds[key]:
            to_add += f" <kbd>{bind}</kbd>"
        to_add += f" | {values['display_name']} |"
        page += to_add
    page += """
## alternate layers
"""
    for layer, sub_schema in sub_schemas.items():
        page += f"""
### `{layer}`
{sub_schema["description"]}

| action | default hotkey | description |
| ------ | -------------- | ----------- |"""
        for key, values in sub_schema["properties"].items():
            to_add = f"\n| {key} |"
            if isinstance(sub_keys[layer][key], str):
                sub_keys[layer][key] = [sub_keys[layer][key]]
            for bind in sub_keys[layer][key]:
                to_add += f" <kbd>{bind}</kbd>"
            to_add += f" | {values['display_name']} |"
            page += to_add
    # handle subkeys now thanks
    with open(
        "docs/src/content/docs/reference/keybindings.mdx", "w", encoding="utf-8"
    ) as file:
        file.write(page)
    invoker = []
    executor = ""
    if executor := which("prettier"):
        invoker = [executor]
    elif executor := which("npx"):
        invoker = [executor, "prettier"]
    elif executor := which("npm"):
        invoker = [executor, "exec", "prettier"]
    else:
        pprint(
            "[red][blue]prettier[/] and [blue]npx[/] are not available on PATH, and hence the generated files cannot be formatted."
        )
        exit(1)
    # attempt to format it
    try:
        run(
            invoker
            + [
                "--write",
                "docs/src/content/docs/reference/keybindings.mdx",
            ],
            check=True,
        )
    except CalledProcessError:
        pprint(
            f"[red]Failed to generate [bright_blue]keybindings.mdx[/] after {precisedelta(perf_counter() - start_time, minimum_unit='milliseconds')}[/]"
        )
    pprint(
        f"[green]Generated [bright_blue]keybindings.mdx[/] in {precisedelta(perf_counter() - start_time, minimum_unit='milliseconds')}[/]"
    )
except FileNotFoundError:
    pprint("[red]Do not run manually with python! Run [blue]poe gen-keys[/][/]")
    pprint(Traceback(show_locals=True))
    exit(1)
