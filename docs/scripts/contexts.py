import ast
from pathlib import Path

ROOT = Path(__file__).parents[2]
SOURCE = ROOT / "src" / "rovr"
OUTPUT = SOURCE / "variables" / "maps.py"


def contexts_in(source: str) -> set[str]:
    contexts = set()
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Assign) or not any(
            isinstance(target, ast.Name) and target.id == "key_contexts"
            for target in node.targets
        ):
            continue
        value = ast.literal_eval(node.value)
        contexts.update(value)
    return contexts


contexts = {"global", "main"}
for source_path in SOURCE.rglob("*.py"):
    contexts.update(contexts_in(source_path.read_text(encoding="utf-8")))

entries = "\n".join(f'    "{context}",' for context in sorted(contexts))
source = OUTPUT.read_text(encoding="utf-8")
assignment = next(
    node
    for node in ast.walk(ast.parse(source))
    if isinstance(node, ast.Assign)
    and any(
        isinstance(target, ast.Name) and target.id == "VALID_KEY_CONTEXTS"
        for target in node.targets
    )
)
replacement = f"""VALID_KEY_CONTEXTS = frozenset({{
{entries}
}})
"""
lines = source.splitlines(keepends=True)
lines[assignment.lineno - 1 : assignment.end_lineno] = [replacement]
OUTPUT.write_text("".join(lines), encoding="utf-8")
