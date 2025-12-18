import json
from shutil import which
from subprocess import CalledProcessError, run
from time import perf_counter

from humanize import precisedelta
from json_schema_for_humans.generate import generate_from_filename
from json_schema_for_humans.generation_configuration import GenerationConfiguration
from rich.console import Console
from rich.traceback import Traceback

from rovr.config.models import RovrConfig

start_time = perf_counter()
pprint = Console().print

try:
    # Generate JSON schema from Pydantic model
    schema = RovrConfig.model_json_schema()
    # Add JSON Schema metadata
    schema["$schema"] = "https://json-schema.org/draft-07/schema"
    schema["title"] = "Rovr Config"

    # Write the generated schema to schema.json
    with open("src/rovr/config/schema.json", "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)

    pprint(
        f"[green]Generated [bright_blue]schema.json[/] from Pydantic models in {precisedelta(perf_counter() - start_time, minimum_unit='milliseconds')}[/]"
    )

    config = GenerationConfiguration()
    if config.template_md_options is not None:
        config.template_md_options["properties_table_columns"] = [
            "Property",
            "Type",
            "Title/Description",
        ]
    config.template_name = "md"
    config.with_footer = False
    # Store the original schema content for restoration
    with open("src/rovr/config/schema.json", "r", encoding="utf-8") as f:
        original_schema_content = f.read()
    # Do some temporary fixes to the schema for markdown generation
    with open("src/rovr/config/schema.json", "w", encoding="utf-8") as f:
        f.write(
            original_schema_content.replace("|", "&#124;")
            .replace(">", "&gt;")
            .replace("<", "&lt;")
        )
    try:
        generate_from_filename(
            "src/rovr/config/schema.json",
            "docs/src/content/docs/reference/schema.mdx",
            config=config,
        )
    finally:
        # Restore original schema file
        with open("src/rovr/config/schema.json", "w", encoding="utf-8") as f:
            f.write(original_schema_content)
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
