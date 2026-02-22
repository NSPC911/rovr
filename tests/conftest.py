from unittest.mock import patch

# Patch sys.__stdin__ early (before test collection imports application modules)
# so that textual_image skips terminal queries that require a real TTY.
_stdin_patch = patch("sys.__stdin__", None)
_stdin_patch.start()
