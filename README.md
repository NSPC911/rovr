<div align="center">
  <h1>rovr</h1>
  <img alt="Python Version" src="https://img.shields.io/pypi/pyversions/rovr?style=for-the-badge&logo=python&logoColor=white&color=yellow&label=for" height="24px" width="auto">
  <a href="https://nspc911.github.io/discord"><img alt="Discord" src="https://img.shields.io/discord/1110189201313513552?style=for-the-badge&logoColor=white&color=%235865f2&logo=discord" height="24px" width="auto"></a>
  <a href="https://pypi.org/project/rovr"><img alt="PyPI - Downloads" src="https://img.shields.io/pypi/dw/rovr?style=for-the-badge&logoColor=white&color=darkgreen&label=pip&logo=pypi" height="24px" width="auto"></a>
  <br>
  <img alt="GitHub Actions Docs Build Status" src="https://img.shields.io/github/actions/workflow/status/nspc911/rovr/.github%2Fworkflows%2Fdeploy.yml?style=for-the-badge&label=docs&logo=opencontainersinitiative" height="24px" width="auto">
  <img alt="GitHub Actions Formatting Status" src="https://img.shields.io/github/actions/workflow/status/nspc911/rovr/.github%2Fworkflows%2Fformatting.yml?style=for-the-badge&label=style&logo=opencontainersinitiative" height="24px" width="auto">
  <br>
  <a href="https://terminaltrove.com/rovr">
    <img src="https://terminaltrove.com/static/assets/media/terminal_trove_normal.png" alt="terminal trove" height="24px" width="auto">
  </a>
</div>

> [!warning]
> This project is in its very early stages. While this can be daily driven, expect some issues here and there.

<!--toc:start-->
- [Screenshot](#screenshot)
- [Installation](#installation)
- [Running from source](#running-from-source)
- [FAQ](#faq)
- [License](#license)
- [Stargazers](#stargazers)
<!--toc:end-->

### Screenshot

![image](https://github.com/NSPC911/rovr/blob/master/docs%2Fpublic%2Fscreenshots%2Fmain.png?raw=true)

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
uv run rovr
```

Running in dev mode to see debug outputs and logs
```pwsh
uv run rovr --dev
# or with poethepoet
poe dev
```
the Textual console must also be active to see debug outputs
```pwsh
uv run textual console
# or uvx if not running from source
uvx --from textual-dev textual console
# or just capture print statements
poe log
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
        - If [NeoVim](https://github.com/neovim/neovim) is considered modern, then [Helix](https://github.com/helix-editor/helix) is post-modern
        - If [SuperFile](https://github.com/yorukot/superfile) is considered modern, then [rovr](https://github.com/NSPC911/rovr) is post-modern

3. What can I contribute?
    - Themes, and features can be contributed.
    - Refactors will be frowned on, and may take a longer time before merging.

4. I want to add a feature/theme/etc! How do I do so?
    - You need [uv](https://docs.astral.sh/uv) at minimum. [prek](https://github.com/j178/prek), [ruff](https://docs.astral.sh/ruff) and [ty](https://docs.astral.sh/ty) are recommended to be installed.
    - Clone the repo, and inside it, run `uv sync` and `prek install`.
    - Make your changes, ensure that your changes are properly formatted (via the pre-commit hook), before pushing to a **custom** branch on your fork.
    - For more info, check the [how to contribute](https://nspc911.github.io/rovr/contributing/how-to-contribute) page.

5. How do I make a feature suggestion?
    - Open an issue using the `feature-request` tag, with an estimated difficulty as an optional difficulty level label

6. Why not ratatui or bubbletea??? <sub><i>angry noises</i></sub>
    - I like Python.

7. What's with the name?
    - Kind of a weird thing. [ranger](https://github.com/ranger/ranger) is a terminal file manager written in Python. And there is a car brand named Range Rover. Range~~r~~. Hence, I wanted to use "rover", but there is already an existing file explorer named [rover](https://github.com/lecram/rover), so I just removed the "e" to be a bit more fancy.

8. How should I stylize rovr?
    - Just "rovr", please.

### License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

### Stargazers
Thank you so much for starring this repo! Each star pushes me more to make even more amazing features for you!
<a href="https://www.star-history.com/#nspc911/rovr&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=nspc911/rovr&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=nspc911/rovr&type=Date" />
   <img alt="" src="https://api.star-history.com/svg?repos=nspc911/rovr&type=Date" />
 </picture>
</a>

```
 _ ___  ___ __   _ˍ_ ___
/\`'__\/ __`\ \ /\ \`'__\
\ \ \_/\ \_\ \ V_/ /\ \_/
 \ \_\\ \____/\___/\ \_\
  \/_/ \/___/\/__/  \/_/ by NSPC911
```
