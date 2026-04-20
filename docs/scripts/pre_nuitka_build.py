from importlib import resources

from rich.console import Console

console = Console()

try:
    content = (
        resources.files("nuitka.plugins.standard")
        / "standard.nuitka-package.config.yml"
    ).read_text()
    if "textual.widgets" in content:
        splitted = content.splitlines()
        new_content = splitted[:7700]
        start_ignoring = False
        for line in splitted[7700:8500]:
            if 'module-name: "textual.widgets"' in line:
                start_ignoring = True
                continue
            elif start_ignoring:
                if line.startswith("- module-name"):
                    start_ignoring = False
                else:
                    continue
            new_content.append(line)
        new_content.extend(splitted[8500:])
        new_content = "\n".join(new_content)
        with open(
            resources.files("nuitka.plugins.standard")
            / "standard.nuitka-package.config.yml",
            "w",
        ) as f:
            f.write(new_content)
except ImportError:
    console.print_exception(extra_lines=3, max_frames=1)
