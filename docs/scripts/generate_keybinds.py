import json
from shutil import which
from subprocess import CalledProcessError, run
from time import perf_counter

import tomli
from humanize import precisedelta
from rich.console import Console
from rich.traceback import Traceback

start_time = perf_counter()
pprint = Console().print

KEY_NAMESPACES = (
    "general",
    "normal",
    "select",
    "extra_copy",
    "change_sort_order",
    "delete_files",
    "filename_conflict",
    "file_in_use",
    "filter_modal",
    "yes_or_no",
)
NESTED_KEY_NAMESPACES = set(KEY_NAMESPACES[3:])


def format_keybinds(keys: str | list[str] | None) -> str:
    if keys is None:
        return "*none*"
    if isinstance(keys, str):
        keys = [keys]
    if not keys:
        return "*none*"
    return " ".join(f"<kbd>{k}</kbd>" for k in keys)


def get_nested_key(data: dict, *keys: str) -> str | list[str] | None:
    for key in keys:
        if isinstance(data, dict) and key in data:
            data = data[key]
        else:
            return None
    if isinstance(data, (str, list)):
        return data
    return None


def compile_legacy_keybinds(config_data: dict) -> dict:
    if not isinstance(config_data.get("keys"), dict):
        return config_data.get("keybinds", {})
    keys_config = config_data["keys"]
    keybinds: dict = {}
    for namespace in KEY_NAMESPACES:
        keymap = keys_config.get(namespace, {})
        if not isinstance(keymap, dict):
            continue
        for key, action in keymap.items():
            if namespace in NESTED_KEY_NAMESPACES:
                keybinds.setdefault(namespace, {}).setdefault(action, []).append(key)
            elif action.startswith("plugin_"):
                continue
            else:
                keybinds.setdefault(action, []).append(key)
    if isinstance(keybinds.get("command_palette"), list):
        keybinds["command_palette"] = keybinds["command_palette"][0]
    return keybinds


page = """
---
title: Keybindings
description: A reference for all default keybindings in rovr.
---
{/* do not directly modify this file, modify the template in docs/scripts/generate_keybinds.py */}

import { Aside } from "@astrojs/starlight/components"

this page provides a comprehensive list of the default keybindings in `rovr`. you can customize these keybindings in your `config.toml` file.

<Aside type="tip">
  you can make use of the cli arg `--show-keys` to view the key that you just pressed to help you in configuring your keybinds!
</Aside>

## keybind profiles
rovr provides two pre-configured keybind profiles that you can use as a starting point:

### sane profile
find this profile at `src/rovr/config/keybinds/sane.toml` in the repository.<br/>the **sane** profile is designed for users who prefer more traditional keybindings

### vim profile
find this profile at `src/rovr/config/keybinds/vim.toml` in the repository.<br/>the **vim** profile is tailored for users familiar with vim-style keybindings

### using a profile
just copy over the contents of the desired profile into your `config.toml` file located at:
- linux/macos: `~/.config/rovr/config.toml`
- windows: `%APPDATA%/rovr/config.toml`

## main bindings

| action | description | default | vim | sane |
| ------ | ----------- | ------- | --- | ---- |"""
try:
    with open("src/rovr/config/config.toml", "rb") as file:
        binds: dict = compile_legacy_keybinds(tomli.load(file))
    with open("src/rovr/config/keybinds/vim.toml", "rb") as file:
        vim_binds: dict = compile_legacy_keybinds(tomli.load(file))
    with open("src/rovr/config/keybinds/sane.toml", "rb") as file:
        sane_binds: dict = compile_legacy_keybinds(tomli.load(file))
    with open("src/rovr/config/schema.json", "r", encoding="utf-8") as file:
        sub_schema: dict = json.load(file)["properties"]["keybinds"]["properties"]
    sub_schemas: dict[str, dict] = {}
    sub_keys: dict[str, dict] = {}
    for key, values in sub_schema.items():
        if isinstance(binds[key], dict):
            sub_schemas[key] = values
            sub_keys[key] = binds[key]
            continue
        default_keys = format_keybinds(binds[key])
        vim_keys = format_keybinds(vim_binds.get(key, []))
        sane_keys = format_keybinds(sane_binds.get(key, []))
        page += f"\n| {key} | {values['display_name']} | {default_keys} | {vim_keys} | {sane_keys} |"
    page += """
## alternate layers

keybinds related to the alternate screens and popups in rovr.
"""
    for layer, schema in sub_schemas.items():
        page += f"""
### `{layer}`
{schema["description"]}

| action | default | vim | sane | description |
| ------ | ------- | --- | ---- | ----------- |"""
        for key, values in schema["properties"].items():
            default_keys = format_keybinds(sub_keys[layer].get(key, []))
            vim_keys = format_keybinds(get_nested_key(vim_binds, layer, key))
            sane_keys = format_keybinds(get_nested_key(sane_binds, layer, key))
            page += f"\n| {key} | {default_keys} | {vim_keys} | {sane_keys} | {values['display_name']} |"
    # handle subkeys now thanks
    with open(
        "docs/src/content/docs/dev/reference/keybindings.mdx", "w", encoding="utf-8"
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
                "docs/src/content/docs/dev/reference/keybindings.mdx",
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
except Exception:
    pprint(Traceback(show_locals=True))
    exit(1)
