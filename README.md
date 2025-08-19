<div align="center">
  <h1>rovr</h1>
  <img alt="Static Badge" src="https://img.shields.io/badge/Python-3.13-yellow?style=for-the-badge">
  <img alt="Static Badge" src="https://img.shields.io/badge/made_with-textual-0b171d?style=for-the-badge&logoColor=yellow">
  <!--python -c "import toml;print(len(toml.load('uv.lock')['package']))"-->
  <img alt="Static Badge" src="https://img.shields.io/badge/Dependencies-77-purple?style=for-the-badge">
</div>

> [!caution]
> This project is in its very early stages. Feedback is appreciated, but this cannot be daily-driven yet.

<!--toc:start-->

- [What and Why?](#what-and-why)
- [Installation](#installation)
- [Screenshots](#screenshots)
- [FAQ](#faq)
- [Road map](#road-map)
  - [Version 1](#version-1)
  - [Version 2](#version-2)
  <!--toc:end-->

### What and Why?

- What:
  - It is a file manager made using the Textual framework.
- Why:
  - Because I can :3
  - I'm using this as a learning opportunity to learn more about Textual, and designing a neat little app for myself.

### Installation

```pwsh
# Test the main branch
uvx --from git+https://github.com/NSPC911/rovr.git -q rovr --python 3.13
# Install
## uv (my fav)
uv tool install rovr
## or pipx
pipx install rovr
## or plain old pip
pip install rovr
```

### Screenshots

Startup
<img alt="Version 0.0.0.4" src="https://github.com/NSPC911/rovr/blob/master/img/0.0.0.4/rovr_main.png?raw=true">

Create new Item
<img alt="Version 0.0.0.4" src="https://github.com/NSPC911/rovr/blob/master/img/0.0.0.4/rovr_new.png?raw=true">

Delete selected items
<img alt="Version 0.0.0.4" src="https://github.com/NSPC911/rovr/blob/master/img/0.0.0.4/rovr_delete.png?raw=true">

Zoxide integration
<img alt="Version 0.0.0.4" src="https://github.com/NSPC911/rovr/blob/master/img/0.0.0.4/rovr_zoxide.png?raw=true">

### FAQ

1. There isn't X theme/Why isn't Y theme available?

- Textual's currently available themes are limited. However, extra themes can be added via the config file in the format below
- You can take a look at what each color represents in https://textual.textualize.io/guide/design/#base-colors<br>Inheriting themes will **not** be added.

```toml
[[custom_theme]]
name = "<str>"
primary = "<hex>"
secondary = "<hex>"
success = "<hex>"
warning = "<hex>"
error = "<hex>"
accent = "<hex>"
foreground = "<hex>"
background = "<hex>"
surface = "<hex>"
panel = "<hex>"
is_dark = "<bool>"
variables = {
  "<key>" = "<value>"
}
```

2. Why is it considered post-modern?

- Parody to my current editor, [helix](https://helix-editor.com)
  - If NeoVim is considered modern, then Helix is post-modern
  - If superfile is considered modern, then rovr is post-modern

3. Why did you say it cannot be daily driven?

- Refer to the road map. There is many features yet to be completed. Pull Requests are appreciated

4. What can I contribute?

- Themes, and features can be contributed.
- Refactors will be frowned on, and may take a longer time before merging.

5. I want to add a feature/theme/etc! How do I do so?

- You need [uv](https://docs.astral.sh/uv) at minimum. [pre-commit](https://pre-commit.com/) and [ruff](https://docs.astral.sh/ruff) are recommended to be installed.
- Clone the repo, and inside it, run `uv sync` and `pre-commit install`.
- Make your changes, ensure that your changes are properly formatted (via the pre-commit hook), before pushing to a **custom** branch on your fork.

6. How do I make a feature suggestion?

- Open an issue using the `feature-request` tag. Issue templates will come soon.

7. Why not ratatui or bubbletea??? <sub><i>angry noises</i></sub>

- I like python.

8. When will it be completed?

- When it is completed.

### Road map

This is a list of features that I plan to add before releasing the appropriate version and where they are inspired from.

#### Version 1

Status: 33/33

- [x] Directory Auto-completion (explorer)
- [x] Button Navigation (explorer)
- Keyboard Navigation
  - [x] Directory Navigation (explorer)
  - [x] Others (superfile)
- [x] Double Click to enter into directories (explorer)
- Configuration (superfile)
  - [x] Base
  - [x] Schema
  - [x] Extending custom themes via configuration
- [x] [zoxide](https://github.com/ajeetdsouza/zoxide) support (ranger)<br><sub>There is no command line for rovr, which means it will use keybinds to launch either a modified current folder bar or a panel</sub>
- Previewing files
  - [x] Image files using [textual-image](https://github.com/lnqs/textual-image) (superfile)<br><sub>Explorer kinda supports image viewing, but this is a TUI, so inspiration is from superfile</sub>
  - [x] Directories (superfile)
  - Compressed Files
    - [x] `.zip`
    - [x] `.tar`, `.gz` and the family
- [x] Pinned folder sidebar (superfile)<br><sub>Explorer also supports a pinned sidebar, but it also includes the massive file tree, which I won't add.</sub>
- [x] Search Bar (superfile)
- [x] Metadata
- Clipboard (superfile)
  - [x] Copy files and folders
  - [x] Cut files and folders
  - [x] Paste files and folders
    - [x] Warn when overwriting same named files
- Multiple File Lists
  - [x] Tabs
- [x] Active and Completed processes (superfile)
- Actions bar (explorer)
  - [x] Copy files
  - [x] Cut files
  - [x] Paste files
  - [x] Create new files/folders
  - [x] Delete files/folders
  - [x] Rename **a** file/folder
  - Extract from compressed archive
    - [x] `.zip`
    - [x] `.tar`, `.gz` and the family
  - Compress to archive
    - [x] `.zip`
    - [x] `.tar`, `.gz` and the family
- [x] bat as previewer

#### Version 2

- [ ] Plugins using [pytest-dev/pluggy](https://github.com/pytest-dev/pluggy) or a custom way (I wish not)
- [ ] Cross process clipboard sync (two rovr instances should have synced clipboards)
- [ ] Recycle Bin of 1-day when files get overwritten (Currently handled with `sendtotrash` but it doesn't work at times, so not a reliable solution)

#### Declined Features

- Horizontal and Vertical Splits
  - Too much clutter in a single window, especially when tabs already exist.
- Transparent UI
  - Some issues with Textual as a whole prevents me from creating a transparent UI.
- Change sort order of files
  - Too much work. However, if you are willing to put in the time for it, I'm glad to merge it!
