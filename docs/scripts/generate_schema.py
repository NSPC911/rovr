from json_schema_for_humans.generate import generate_from_filename
from json_schema_for_humans.generation_configuration import GenerationConfiguration

config = GenerationConfiguration()
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
with open("docs/src/content/docs/reference/schema.mdx", "r") as schema_file:
    content = schema_file.read()
with open("docs/src/content/docs/reference/schema.mdx", "w") as schema_file:
    schema_file.write(
        """---\ntitle: schema for humans\ndescription: config schema humanified\n---"""
        + content[13:].replace("| - ", "|   ").replace("| + ", "|   ")
    )
