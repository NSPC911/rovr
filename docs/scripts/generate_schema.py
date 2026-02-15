from shutil import which
from subprocess import CalledProcessError, run
from time import perf_counter

from humanize import precisedelta
from rich.console import Console
from rich.traceback import Traceback

start_time = perf_counter()
pprint = Console().print

try:
    import json_schema_for_humans as jsfh  # ty: ignore # noqa
except ImportError:
    pprint(
        "[red]json-schema-for-humans is not installed. Make sure to install the \\[docscripts] group as well!"
    )

schema_content: str | None = None
try:
    config = jsfh.generation_configuration.GenerationConfiguration()
    if config.template_md_options is not None:
        config.template_md_options["properties_table_columns"] = [
            "Property",
            "Type",
            "Title/Description",
        ]
    config.template_name = "md"
    config.with_footer = False
    # do some temporary fixes to the schema
    with open("src/rovr/config/schema.json", "r", encoding="utf-8") as f:
        schema_content = f.read()
    with open("src/rovr/config/schema.json", "w", encoding="utf-8") as f:
        f.write(
            schema_content.replace("|", "&#124;")
            .replace(">", "&gt;")
            .replace("<", "&lt;")
        )
    jsfh.generate.generate_from_filename(
        "src/rovr/config/schema.json",
        "docs/src/content/docs/reference/schema.mdx",
        config=config,
    )
    with open(
        "docs/src/content/docs/reference/schema.mdx", "r", encoding="utf-8"
    ) as schema_file:
        content = schema_file.read()
    with open(
        "docs/src/content/docs/reference/schema.mdx", "w", encoding="utf-8"
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
                "docs/src/content/docs/reference/schema.mdx",
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
        with open("src/rovr/config/schema.json", "w", encoding="utf-8") as f:
            f.write(schema_content)
