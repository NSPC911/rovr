import json
from pathlib import Path

import fastjsonschema

schema = json.loads(Path("src/rovr/assets/schema.json").read_text(encoding="utf-8"))
Path("src/rovr/_schema_validator.py").write_text(
    fastjsonschema.compile_to_code(schema), encoding="utf-8"
)
