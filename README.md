<div align="center">
  <h1>rovr</h1>
  <img alt="Python Version" src="https://img.shields.io/pypi/pyversions/rovr?style=for-the-badge&logo=python&logoColor=white&color=yellow">
  <img alt="Made with Textual" src="https://img.shields.io/badge/made_with-textual-0b171d?style=for-the-badge&logoColor=white">
  <img alt="Static Badge" src="https://img.shields.io/badge/Linter-Ruff_%2B_ty-black?style=for-the-badge&color=24122d">
  <br>
  <a href="https://nspc911.github.io/discord"><img alt="Discord" src="https://img.shields.io/discord/1110189201313513552?style=for-the-badge&logo=discord&logoColor=white&color=%235865f2"></a>
  <a href="https://pypi.org/project/rovr"><img alt="PyPI - Downloads" src="https://img.shields.io/pypi/dw/rovr?style=for-the-badge&logo=pypi&logoColor=white&color=darkgreen"></a>
  <br>
  <img alt="GitHub Actions Docs Build Status" src="https://img.shields.io/github/actions/workflow/status/nspc911/rovr/.github%2Fworkflows%2Fdeploy.yml?style=for-the-badge&label=docs">
  <img alt="GitHub Actions Formatting Status" src="https://img.shields.io/github/actions/workflow/status/nspc911/rovr/.github%2Fworkflows%2Fformatting.yml?style=for-the-badge&label=style">
</div>

> [!warning]
> This project is in its very early stages. While this can be daily driven, expect some issues here and there.

<!--toc:start-->

- [Screenshot](#screenshot)
- [Installation](#installation)
- [Running from source](#running-from-source)
- [FAQ](#faq)
- [Stargazers](#stargazers)
<!--toc:end-->

### Screenshot

![image](https://github.com/NSPC911/rovr/blob/master/img%2F0.1.0%2Frovr_main.png?raw=true)

### Installation

```pwsh
# Test the main branch
uvx git+https://github.com/NSPC911/rovr.git
# Install
## uv (my fav)
uv tool install rovr
## or pipx
pipx install rovr
## or plain old pip
pip install rovr
```

### Running from source

```pwsh
uv run poe run
```

Running in dev mode to see debug outputs and logs
```pwsh
# Runs it in development mode, allowing a connected console
# to capture the output of its print statements
uv run poe dev
# Runs a separate console to capture print statements
uv run poe log
# capture everything
uv run textual console
```
For more info on Textual's console, refer to https://textual.textualize.io/guide/devtools/#console

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
  - If neovim is considered modern, then helix is post-modern
  - If superfile is considered modern, then rovr is post-modern

3. What can I contribute?

- Themes, and features can be contributed.
- Refactors will be frowned on, and may take a longer time before merging.

4. I want to add a feature/theme/etc! How do I do so?

- You need [uv](https://docs.astral.sh/uv) at minimum. [pre-commit](https://pre-commit.com/) and [ruff](https://docs.astral.sh/ruff) are recommended to be installed.
- Clone the repo, and inside it, run `uv sync` and `pre-commit install`.
- Make your changes, ensure that your changes are properly formatted (via the pre-commit hook), before pushing to a **custom** branch on your fork.
- For more info, check the [how to contribute](https://nspc911.github.io/rovr/contributing/how-to-contribute) page.

5. How do I make a feature suggestion?

- Open an issue using the `feature-request` tag, with an estimated difficulty as an optional difficulty level label

6. Why not ratatui or bubbletea??? <sub><i>angry noises</i></sub>

- I like python.


### Stargazers
Thank you so much for starring this repo! Each star pushes me more to make even more amazing features for you!
<a href="https://www.star-history.com/#nspc911/rovr&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=nspc911/rovr&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=nspc911/rovr&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=nspc911/rovr&type=Date" />
 </picture>
</a>

```
 _ ___  ___ __   _ˍ_ ___
/\`'__\/ __`\ \ /\ \`'__\
\ \ \_/\ \_\ \ V_/ /\ \_/
 \ \_\\ \____/\___/\ \_\
  \/_/ \/___/\/__/  \/_/ by NSPC911
```
