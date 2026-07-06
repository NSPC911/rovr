---
title: custom openers
description: configuring custom commands to open specific files or directories.
---

rovr allows you to configure custom commands to open files based on their MIME type or file path pattern. these custom openers are used when you open a file directly.

## configuration

openers are declared as named groups in `settings.openers.groups`, then glob patterns are mapped to one or more of those group names in `settings.openers.match`.

```toml
[settings.openers.groups]
text = [
    { run = "$EDITOR", orphan = true },
    { run = "code", orphan = true }
]
image = [
    "imv"
]
fallback = [
    { run = "explorer.exe", if = { os = ["Windows"] } },
    { run = "xdg-open", if = { os = ["Linux"] } }
]

[settings.openers.match]
"*.py" = ["text"]
"*.png" = ["image"]
"*" = ["fallback"]
```

the matching is done in order of declaration. this means if `"*"` is defined before `"*.py"`, the fallback opener will be used for python files instead of the text opener.

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
[settings.openers.groups]
py = [
    { run = "python", orphan = false, if = { os = ["Linux", "Darwin"] } }
]

[settings.openers.match]
".*\\.py" = ["py"]
```

### adding more openers
currently rovr doesn't set up any default openers, which means it will use whatever your system has set, which is
- `cmd /c start` on Windows
- `open` on MacOS
- `xdg-open` on Linux
