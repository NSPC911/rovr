default:
    @just --list

_hash_dump:
    git rev-parse HEAD > src/rovr/COMMIT_HASH

_warn_dump:
    echo "If you need to change any config, don't change them here!! Look at https://nspc911.github.io/rovr/configuration/configuration/ for more info" > src/rovr/DO_NOT_EDIT_THESE_FILES

_dump_clean:
    uv run python -c "import os; os.path.exists('src/rovr/COMMIT_HASH') and os.remove('src/rovr/COMMIT_HASH'); os.path.exists('src/rovr/DO_NOT_EDIT_THESE_FILES') and os.remove('src/rovr/DO_NOT_EDIT_THESE_FILES')"

_docscripts_setup:
    uv sync --group docscripts

_test_setup:
    uv sync --group test

# Run rovr
run *args:
    uv run rovr {{args}}

# Run rovr in development mode with textual-dev
dev *args:
    uv run textual run --dev rovr.__main__:cli -- {{args}}

# Launch textual's console (need rovr to be launched as dev)
log:
    uv run textual console -x WORKER -x SYSTEM -x DEBUG -x EVENT

# Generate the JSON schema for rovr's config
gen-schema:
    just _docscripts_setup
    uv run docs/scripts/generate_schema.py

# Print all available icons to the terminal for testing
icon-test:
    uv run docs/scripts/icon_test.py

# Generate the keybinds documentation
gen-keys:
    uv run docs/scripts/generate_keybinds.py

# Convert the JSON schema into a Python TypedDict for internal use
schema-to-dict:
    just _docscripts_setup
    uv run jsonschema-gentypes --json-schema ./src/rovr/config/schema.json --python ./src/rovr/classes/config.py
    just format

typed: schema-to-dict

# Run all checks (type checking and linting)
check:
    uv run ty check
    uv run ruff check

# Run ruff related formatters
format:
    uv run ruff check --unsafe-fixes --fix
    uv run ruff format

fmt: format

# Format all SVG screenshots in the docs
screenshot-format:
    pnpx prettier --write "docs/public/screenshots/*.svg" --parser html --bracket-same-line --print-width 160

svg-fmt: screenshot-format

# Start rovr with pyinstrument for flamegraph profiling
flame *args:
    uv run pyinstrument --renderer=html --timeline --use-timing-thread --show-all -m rovr {{args}}

# Take a screenshot after a delay (default: 10s), saved to docs/public/screenshots/
snip filename delay="10":
    uv run textual run --screenshot {{delay}} rovr.__main__:cli --screenshot-path docs/public/screenshots --screenshot-filename {{filename}} -- --without theme.transparent

snap filename delay="10": (snip filename delay)

# Run tokei
tokei *args:
    tokei --sort lines --exclude '*.svg' --exclude 'src/rovr/classes/config.py' --exclude '*lock*' --hidden {{args}}

# Run tests; optionally pass specific files and worker count
test workers="4" *files:
    just _test_setup
    uv run pytest -n {{workers}} {{files}}

# Build rovr into an executable using Nuitka
build mode="onefile" lto="yes" report="report.xml":
    uv sync --group build --extra speedup --no-dev
    just _warn_dump
    just _hash_dump
    uv run nuitka --lto={{lto}} --mode={{mode}} --report={{report}} src/rovr "--onefile-tempdir-spec={TEMP}/rovr_onefile_0.9.1"
    just _dump_clean

# Build rovr distributions using uv and include commit hash
uv-build:
    just _hash_dump
    just _warn_dump
    uv build
    just _dump_clean
