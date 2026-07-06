<!-- <div align="center">
  <h1>rovr</h1>
  <img alt="Python Version" src="https://img.shields.io/pypi/pyversions/rovr?style=for-the-badge&logo=python&logoColor=white&color=yellow&label=for" height="24px" width="auto">
  <a href="https://nspc911.github.io/discord"><img alt="Discord" src="https://img.shields.io/discord/1110189201313513552?style=for-the-badge&logoColor=white&color=%235865f2&logo=discord" height="24px" width="auto"></a>
  <a href="https://pypi.org/project/rovr"><img alt="PyPI - Downloads" src="https://img.shields.io/pypi/dw/rovr?style=for-the-badge&logoColor=white&color=darkgreen&label=pip&logo=pypi" height="24px" width="auto"></a>
  <br>
  <img alt="GitHub Actions Formatting Status" src="https://img.shields.io/github/actions/workflow/status/NSPC911/rovr/.github%2Fworkflows%2Fformatting.yml?style=for-the-badge&logo=opencontainersinitiative&label=style" height="24px" width="auto">
  <img alt="GitHub Actions Docs Build Status" src="https://img.shields.io/github/actions/workflow/status/NSPC911/rovr/.github%2Fworkflows%2Fdocs-build.yml?style=for-the-badge&logo=opencontainersinitiative&label=Docs" height="24px" width="auto">
  <img alt="GitHub Actions Nuitka Build Status" src="https://img.shields.io/github/actions/workflow/status/NSPC911/rovr/.github%2Fworkflows%2Fnuitka-build.yml?style=for-the-badge&logo=opencontainersinitiative&label=build" height="24px" width="auto">
  <br>
  <a href="https://terminaltrove.com/rovr">
    <img src="https://terminaltrove.com/static/assets/media/terminal_trove_normal.png" alt="terminal trove" height="24px" width="auto">
  </a>
</div> -->

## rovr - a stylish, batteries-included terminal file manager.

![image](https://github.com/NSPC911/rovr/blob/master/docs%2Fpublic%2Fscreenshots%2Fmain.png?raw=true)

rovr is a terminal file manager built with Python's [Textual](https://textual.textualize.io) framework. It was born out of a frustration that TUI apps do not support the mouse properly, and I wanted to make a change.

### Features

<!-- fucking hate emojis -->

- **Modern UI**: Built with Textual for a beautiful and functional terminal interface.
- **Highly Customizable**: Tweak themes, borders, icons, and UI elements to match your exact preference. Configs for nearly everything.
- **Batteries Included**: Handles file preview, image preview, archive handling and more without reaching to external software (but still has integrations for popular tools out-of-box)
- **Cross-Platform**: Powered by Python, running smoothly anywhere Python 3.13 is supported. Binaries are also provided.
- **Real Mouse Support**: Full mouse support for navigation, selection, and actions, making it more intuitive to use.

### Project Status

Currently in public beta similar to yazi. rovr follows the major version 0 scheme, meaning whenever the minor version (like `0.7.0` -> `0.8.0`) is done, there are a lot of breaking changes.
I try to minimise them, and guide the user to what had gone wrong and more info on how to fix them, as well as attempt to fix it.

---

### Installation

Quick Test:

```pwsh
## uv
uvx rovr
## pipx
pipx run rovr
```

```pwsh
# Install
## uv (my fav)
uv tool install rovr
## or pipx
pipx install rovr
## or plain old pip
pip install rovr
```

#### Other package managers

With AUR:

```pwsh
# binary
yay -S rovr-bin
# pip version
yay -S rovr
```

With scoop (windows):

```pwsh
scoop bucket add le-bucket https://github.com/NSPC911/le-bucket
scoop install rovr
```

<!--With HomeBrew (macOS/Linux):
```pwsh
brew tap NSPC911/tap
brew install rovr
```-->

With Conda/Pixi:

```pwsh
pixi global install rovr
```

---

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

---

### Contributing

- **What can I contribute?**
  - Themes and features can be contributed.
  - Refactors will be frowned on, and may take a longer time before merging.

- **How do I contribute?**
  - You need [uv](https://docs.astral.sh/uv) at minimum. [prek](https://github.com/j178/prek), [ruff](https://docs.astral.sh/ruff) and [ty](https://docs.astral.sh/ty) are automatically installed.
  - Clone the repo, and inside it, run `uv sync`.
  - Make your changes, ensure that your changes are properly formatted, before pushing to a **custom** branch on your fork.
  - For more info, check the [how to contribute](https://nspc911.github.io/rovr/contributing/how-to-contribute) page.

- **How do I make a feature suggestion?**
  - Open an issue using the `feature-request` tag. Make sure to add details and context to your suggestion.

### FAQ

1. There isn't X theme/Why isn't Y theme available?
   - Textual's currently available themes are limited. However, extra themes can be added via the config file.
   - You can take a look at what each color represents in https://textual.textualize.io/guide/design/#base-colors<br>Inheriting themes will **not** be added.
   - More info on styling can be found in https://nspc911.github.io/rovr/configuration/theming ([dev version](https://nspc911.github.io/rovr/dev/configuration/theming))

2. Why not ratatui (rust) or bubbletea (go), why python, why??? <sub><i>sad, angry, weird compiled noises</i></sub>
   - I like Python, feel free to leave if you hate it.

3. What's with the name?
   - [ranger](https://github.com/ranger/ranger) is a terminal file manager written in Python. And there is a car brand named Range Rover. Add the `r`, you get [ranger](https://github.com/ranger/ranger). Hence, I wanted to use "rover", but there is already an existing file explorer named [rover](https://github.com/lecram/rover), so I just removed the "e" to be a bit more fancy.

4. How should I stylize rovr?
   - Just "rovr", please. You can add backticks to it if you want, so `rovr`, but please don't capitalise any letters.

5. Why should I use rovr?
   - I don't want to sell it to you. I made it for myself. If you don't like it, sure go ahead, use yazi (rust) or superfile (go), or heck even use the cli, I'm not bothered.

6. OhMGee why are there so many borders and so many icons and so many xxx and so many yyy??? <sub><i>more angry noises</i></sub>
   - Keep in mind, you can disable them. The screenshot is my setup, and the default setup. Textual CSS lets you hide things, disable borders, etc etc, so you can make it look however you want.

7. Is this vibe-coded?
   - Depends on the meaning. AI was used in certain parts of the code, especially in [cli functions](https://github.com/NSPC911/rovr/blob/master/src/rovr/functions/cli.py), but aside from that, it is few and far between. However, AI was used to ensure I don't make mistakes while making changes.

---

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
