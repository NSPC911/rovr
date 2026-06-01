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
    { run = "$EDITOR", orphan = true },
    { run = "code", orphan = true }
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
- `orphan` (bool): whether to run the command in a new process detached from rovr.
- `if` (object): criteria that must be met for this opener to be available.

### conditional openers (`if`)

the `if` property allows you to restrict when an opener is used based on specific conditions:

- `os` (array of strings): the operating system(s) where this opener is valid (e.g., `["Windows"]`, `["Linux"]`, `["Darwin"]`).
- `cwd` (array of strings): glob patterns that must match the current working directory.

```toml
[settings.openers]
".*\\.py" = [
    { run = "python", orphan = false, if = { os = ["Linux", "Darwin"] } }
]
```
