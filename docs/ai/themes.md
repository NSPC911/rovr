# The theme system rework (`better-themes-att-2`)

This document describes the changes made to rovr's theming on this branch: what
was changed, how each piece works, and how they combine into a single coherent
system. Written by the AI pair (Anthropic: Claude Fable 5) that implemented it.

## What changed, at a glance

- Themes are now plain `tcss` files instead of `[[custom_theme]]` TOML tables.
- Theme files are hot-reloaded while rovr is running.
- Bundled themes are read straight from the package and can be overridden by a
  user file with the same name.
- Progress-bar gradients moved from config into the theme files.
- Theme files can contain regular tcss rules, applied only while the theme is
  active.
- Parse failures produce readable notifications instead of crashing (or
  printing an object repr).

## The changes in detail

### 1. Theme files (`src/rovr/functions/themes.py`)

A theme is a file named `<name>.tcss` — the stem becomes the theme name. The
file is a list of `$variable: value;` declarations, optionally followed by
regular tcss rules. `parse_theme_file` splits the declarations into three
buckets:

- Names matching `textual.theme.Theme` dataclass fields (`primary`, `dark`,
  `luminosity-spread`, …) become constructor arguments. Routing them through
  the Theme — and therefore through `ColorSystem.generate()` — is what makes an
  overridden `$primary` regenerate `$primary-lighten-3`, `$text-primary`, and
  every other derived shade.
- `$bar-gradient-default` / `$bar-gradient-error` are rovr-specific: their
  colors are validated and attached to the Theme as a `bar_gradient` attribute,
  read by `ProcessContainer` via `getattr` when building progress bars.
- Everything else lands in `Theme.variables` as an ordinary variable.

Whatever remains after blanking the declaration lines is the theme's css and is
attached as a `css` attribute (see §4). `Theme` is a plain non-frozen
dataclass, so the two extra attributes can be set directly; its `__eq__`
compares fields only, which matters for change detection below.

### 2. Bundled vs. user themes

`theme_dirs()` returns the bundled package directory first and the user's
`<config folder>/themes/` second; `register_all_themes` registers both in that
order, so a user file with the same name wins simply by being registered last.
An earlier design copied ("seeded") the bundled files into the user folder, but
that meant edits to a bundled theme in a development checkout never reached the
app, and upgrades never reached users — registering straight from the package
fixed both.

### 3. Hot reload (`src/rovr/app.py`)

The app polls `theme_file_mtimes()` every second (`set_interval`). When the
snapshot differs it re-registers all themes and, if the *active* theme's
definition changed, calls Textual's `_watch_theme` directly — assigning
`self.theme` its current value is a reactive no-op, and a plain `refresh_css`
is not enough because a theme edit can flip dark mode or ansi handling.
Because the Theme dataclass ignores the injected `css` attribute in `__eq__`,
`reload_themes` compares it separately, so a rules-only edit still re-applies.
A successful reload notifies `Reloaded <files> in N ms`, mirroring the existing
style.tcss notification; failures notify per-file "Theme Error" messages
instead.

### 4. CSS rules in theme files

Textual keeps `refresh_css` as a *reparse of existing sources*, and toggles a
`-theme-<name>` class on the App on every switch. That allowed a very small
design: the active theme's rules are injected as one dedicated stylesheet
source (`Application.THEME_CSS_SOURCE`) and swapped in `_load_theme_css`,
which `_watch_theme` runs before Textual reparses. Only the active theme's
rules are ever loaded, so theme files never need to scope their selectors.

Two subtleties:

- On equal specificity Textual keeps the rule from the last source, which
  would let rovr's own `style.tcss` shadow every theme rule using the same
  selector. The theme source is added with `tie_breaker=1` — the tie breaker is
  the *last* element of the specificity tuple, so it breaks exact ties without
  beating a more specific `style.tcss` selector (e.g. the `:focus-within`
  border rules still win, as they should).
- The new css is parsed on a **trial copy** of the stylesheet first. If it
  fails, the previous css stays in place and the user gets a notification
  listing `line N: <summary>` for each error (unpacked from
  `StylesheetParseError.errors`, whose `str()` is just an object repr), with
  rich markup stripped. A broken theme can therefore never take the app down,
  including at startup.

### 5. Removal of `[[custom_theme]]`

The TOML theme tables, their schema block, the `RovrThemeClass` dataclass, and
the startup exit path for color parse errors were all deleted; `migration.json`
gained an entry that shows old-config users a boxed message explaining the
file-based replacement, key by key. Gradients — the last thing only config
could express — moved into the theme files (§1), which is what made the removal
possible.

## How it comes together

Each piece exists because of the others. Files instead of TOML made themes
*watchable*, which made hot reload natural. Hot reload made editing themes a
live activity, which made readable error reporting mandatory — an edit mid-typo
must degrade to a notification, never a crash. Registering bundled themes from
the package made the same watch/override loop work identically in a dev
checkout and an installed copy. And once every theme was a tcss file with a
known parse step, letting the non-declaration remainder of the file be real
css was a short step: the variables define the palette, the rules restyle
widgets with it, both hot-reload together, and both fail soft.

The result is one mental model for the user: *a theme is a tcss file*. Drop it
in the folder, it appears in the picker; edit it, the app follows; break it,
the app tells you where; name it after a bundled theme, it replaces it.
