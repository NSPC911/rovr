from typing import override

from nuitka.plugins.PluginBase import NuitkaPluginBase  # ty: ignore[unresolved-import]


class NuitkaPluginBytecodeAll(NuitkaPluginBase):
    plugin_name = "bytecode-all"

    @override
    def decideCompilation(self, module_name: object) -> None:
        name = str(module_name)
        if name.startswith("__") or name.endswith(("-preLoad", "-postLoad")):
            return None
        return "bytecode"  # ty: ignore
