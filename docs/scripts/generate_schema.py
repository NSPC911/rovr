from shutil import which
from subprocess import run
from time import perf_counter

from humanize import naturaldelta
from json_schema_for_humans.generate import generate_from_filename
from json_schema_for_humans.generation_configuration import GenerationConfiguration
from rich.console import Console

start_time = perf_counter()
pprint = Console().print

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
    generate_from_filename(
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
    if which("prettier"):
        run(
            ["prettier", "--write", "docs/src/content/docs/reference/schema.mdx"],
            shell=True,
        )
    elif which("npm"):
        run(
            [
                "npx",
                "prettier",
                "--write",
                "docs/src/content/docs/reference/schema.mdx",
            ],
            shell=True,
        )
    else:
        pprint(
            "[red][blue]prettier[/] and [blue]npx[/] are not available on PATH, and hence the generated files cannot be formatted."
        )
        exit(1)
    pprint(
        f"[green]Generated it in {naturaldelta(perf_counter() - start_time, minimum_unit='microseconds')}"
    )
except FileNotFoundError:
    pprint("[red]Do not run manually with python! Run [blue]poe gen-keys[/][/]")
    exit(1)
