import json
import re
from shutil import which
from subprocess import CalledProcessError, run
from time import perf_counter
from urllib.parse import quote

from humanize import precisedelta
from rich.console import Console
from rich.traceback import Traceback

start_time = perf_counter()
pprint = Console().print

try:
    from json_schema_for_humans.generate import generate_from_filename  # noqa  # ty: ignore
    from json_schema_for_humans.generation_configuration import GenerationConfiguration  # noqa  # ty: ignore
except ImportError:
    pprint(
        "[red]json-schema-for-humans is not installed. Make sure to install the \\[docscripts] group as well!"
    )
    exit(1)

schema_content: str | None = None
try:
    config = GenerationConfiguration()
    if config.template_md_options is not None:
        config.template_md_options["properties_table_columns"] = [
            "Property",
            "Type",
            "Title/Description",
        ]
    config.template_name = "md"
    config.with_footer = False
    config.show_toc = False
    config.expand_buttons = True
    # do some temporary fixes to the schema
    with open("src/rovr/assets/schema.json", "r", encoding="utf-8") as f:
        schema_content = f.read()
    with open("src/rovr/assets/schema.json", "w", encoding="utf-8") as f:
        f.write(
            schema_content
            .replace("|", "&#124;")
            .replace(">", "&gt;")
            .replace("<", "&lt;")
        )
    generate_from_filename(
        "src/rovr/assets/schema.json",
        "docs/src/content/docs/dev/reference/schema.mdx",
        config=config,
    )
    with open(
        "docs/src/content/docs/dev/reference/schema.mdx", "r", encoding="utf-8"
    ) as schema_file:
        content = schema_file.read()
    previewer_pattern = next(
        iter(
            json.loads(schema_content)["properties"]["settings"]["properties"][
                "previewers"
            ]["patternProperties"]
        )
    )
    escaped_pattern = previewer_pattern.replace("|", "&#124;")
    content = (
        content
        .replace(f" > {escaped_pattern}", " > previewer name")
        .replace(f"`{escaped_pattern}`", f"`{previewer_pattern}`")
        .replace(quote(escaped_pattern), quote(previewer_pattern))
    )
    content = re.sub(
        r"\[[^\]\n]+\]\(#settings_previewers_pattern1\s*\)",
        "[previewer name](#settings_previewers_pattern1)",
        content,
    )
    with open(
        "docs/src/content/docs/dev/reference/schema.mdx", "w", encoding="utf-8"
    ) as schema_file:
        schema_file.write(
            """---\ntitle: schema for humans\ndescription: config schema humanified\n---"""
            + content[13:].replace("| - ", "|   ").replace("| + ", "|   ")
        )
    invoker = []
    executor = ""
    if executor := which("prettier"):
        invoker = [executor]
    elif executor := which("npx"):
        invoker = [executor, "prettier"]
    elif executor := which("npm"):
        invoker = [executor, "exec", "prettier"]
    else:
        pprint(
            "[red][blue]prettier[/] and [blue]npx[/] are not available on PATH, and hence the generated files cannot be formatted."
        )
        exit(1)
    # attempt to format it
    try:
        run(
            invoker
            + [
                "--write",
                "docs/src/content/docs/dev/reference/schema.mdx",
            ],
        )
    except CalledProcessError:
        pprint(
            f"[red]Failed to generate [bright_blue]schema.mdx[/] after {precisedelta(perf_counter() - start_time, minimum_unit='milliseconds')}[/]"
        )
    pprint(
        f"[green]Generated [bright_blue]schema.mdx[/] in {precisedelta(perf_counter() - start_time, minimum_unit='milliseconds')}[/]"
    )
except FileNotFoundError:
    pprint("[red]Do not run manually with python! Run [blue]poe gen-schema[/][/]")
    pprint(Traceback(show_locals=True))
    exit(1)
except Exception:
    pprint(Traceback(show_locals=True))
    exit(1)
finally:
    # rewrite schema file
    if schema_content is not None:
        with open("src/rovr/assets/schema.json", "w", encoding="utf-8") as f:
            f.write(schema_content)
