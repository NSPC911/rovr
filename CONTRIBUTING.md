# Contributing to rovr

First off, thank you for considering contributing to rovr! It's people like you that make rovr such a great tool.

## Where do I go from here?

If you've noticed a bug or have a feature request, [make one](https://github.com/NSPC911/rovr/issues/new/choose)! It's generally best to check if one already exists before making a new one.

## Fork & create a branch

If you've decided to contribute, you'll want to fork the repository and create a new branch.

```bash
git clone https://github.com/<your-username>/rovr.git
cd rovr
git checkout -b my-new-feature
```

## Development

`rovr` uses `uv` for dependency management.

To set up the development environment, run:
```bash
uv sync --dev
```

`uv` handles venvs for you, but if necessary, activate it by running:
```bash
source .venv/bin/activate
```
(On Windows, you might need to run `.venv\Scripts\activate`)

### Code Style and Linting

We use `ruff` for formatting and linting. Before committing, please run:
```bash
ruff format
```

We also use `ty` for type checking.
```bash
ty check
```

### Committing your changes

We follow the [Conventional Commits](https://www.conventionalcommits.org) specification.
To help with this, you can use `commitizen`, which is included as a dev dependency.
Run `uv run cz c` to create a commit with commitizen.

### Making a Pull Request

When you're ready to make a pull request, please ensure you do the following:

- [ ] I have run `ruff format` to format the code and `ty check` to ensure proper typing.
- [ ] I have tested both the dev version and the built version of rovr.
- [ ] Cache, logs and others are not accidentally added to git's tracking history.
- [ ] My commits follow the conventional commits format.
- [ ] The documentation has been updated if necessary.

If your PR is addressing an issue, please link it in the PR description (e.g., "Fixes #123").

## Types of Contributions

### Bug Fixes

If you are fixing a bug, please create an issue first if one does not already exist. This helps to track the bug and the fix.

### Feature Additions

New features are welcome!

### Theme Additions

If you've created a cool theme for rovr, we'd love to see it! Please make a pull request with your theme, following the `custom_theme` schema. Don't forget to include screenshots as described in the documentation.

Thank you for your contribution!
