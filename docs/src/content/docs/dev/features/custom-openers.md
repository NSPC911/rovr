---
title: custom openers
description: configuring custom commands to open specific files or directories.
---

rovr allows you to configure custom commands to open files based on their MIME type or file path pattern. these custom openers are used when you open a file directly.

## configuration

you can define your custom openers in the `settings.openers` section of your configuration file. the keys are glob patterns that match against the file's MIME type or path, and the values are lists of opener definitions.

```toml
[settings.openers]
"*.py" = [
    { run = "$EDITOR", app = "suspend" },
    { run = "code", app = "orphan" }
]
"*.png" = [
    "imv"
]
"*" = [
    { run = "explorer.exe", if = { os = ["Windows"] } },
    { run = "xdg-open", if = { os = ["Linux"] } }
]
```

if a `*` key is provided, it acts as a fallback for any unmatched file. if no custom opener matches, rovr will fall back to the operating system's default opener.

## opener definitions

an opener can be defined simply as a string representing the command, or as an object for more granular control.

when using an object, the following properties are available:

- `run` (string): the command to execute.
- `app` (string): how rovr should handle the execution. valid options are:
  - `suspend`: suspends rovr until the command finishes (ideal for terminal editors).
  - `block`: blocks rovr in the background until the command finishes.
  - `orphan`: launches the command independently so it remains running even if rovr is closed (ideal for gui apps).
- `if` (object): criteria that must be met for this opener to be available.

### conditional openers (`if`)

the `if` property allows you to restrict when an opener is used based on specific conditions:

- `os` (array of strings): the operating system(s) where this opener is valid (e.g., `["Windows"]`, `["Linux"]`, `["Darwin"]`).
- `cwd` (array of strings): glob patterns that must match the current working directory.
- `directory` (boolean): set to `true` to only apply this opener to directories, or `false` for files only.

```toml
[settings.openers]
".*\\.py" = [
    { run = "python", app = "block", if = { os = ["Linux", "Darwin"], directory = false } }
]
```
