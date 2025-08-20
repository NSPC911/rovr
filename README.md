<div align="center">
  <pre><code>  ___ ___ _ _ ___
  |  _| . | | |  _|
  |_| |___|\_/|_|  </code></pre>
  <img alt="Static Badge" src="https://img.shields.io/badge/Python-3.13-yellow?style=for-the-badge">
  <img alt="Static Badge" src="https://img.shields.io/badge/made_with-textual-0b171d?style=for-the-badge&logoColor=yellow">
  <!--python -c "import toml;print(len(toml.load('uv.lock')['package']))"-->
  <img alt="Static Badge" src="https://img.shields.io/badge/Dependencies-77-purple?style=for-the-badge">
</div>

> [!caution]
> This project is in its very early stages. Feedback is appreciated, but this cannot be daily-driven yet.

<!--toc:start-->

- [Installation](#installation)
- [Screenshots](#screenshots)
- [FAQ](#faq)
<!--toc:end-->

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
