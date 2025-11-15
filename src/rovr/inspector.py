from rich.style import Style
from rich.text import TextType
from rovr.validators import ColorValidator, LayoutValidator, StyleValidator
from textual import events, on, work
from textual.app import ComposeResult
from textual.color import Color
from textual.containers import HorizontalGroup, VerticalGroup, VerticalScroll
from textual.css.query import NoMatches
from textual.css.styles import RulesMap
from textual.dom import DOMNode
from textual.layouts.grid import GridLayout
from textual.layouts.horizontal import HorizontalLayout
from textual.layouts.vertical import VerticalLayout
from textual.validation import Number
from textual.widgets import Input, Label, Static, TabbedContent, Tree
from textual.widgets.tree import TreeDataType, TreeNode

from rovr.resizebar import HorizontalResizeBar, VerticalResizeBar


class DOMTree(Tree):
    DEFAULT_CSS = """
    DOMTree {
        background: transparent;
        height: 1fr
    }
    """

    def __init__(
        self,
        label: TextType,
        data: TreeDataType | None = None,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(
            label, data, name=name, id=id, classes=classes, disabled=disabled
        )


class Inspector(HorizontalGroup):
    DEFAULT_CSS = """
    Inspector {
        dock: right;
        width: 0.25fr;
        &.-hide {
            width: 0;
        }
        #tabcontentwrapper {
            height: 0.5fr
        }
        #css {
            Input {
                border: none !important;
                height: 1;
                padding: 0;
                scrollbar-size: 0 0 !important;
                overflow: hidden hidden;
                width: 0.875fr;
            }
            Static {
                border-right: solid $foreground !important;
                width: 1.125fr;
                text-wrap: nowrap;
                text-overflow: ellipsis
            }
        }
        #id, #classes {
            Label {
                height: 3;
                padding: 1;
                width: 9;
                text-align: center;
                .input--placeholder {
                    color: $foreground-darken-1
                }
            }
            Input {
                width: 1fr;
            }
        }
        &:focus HorizontalResizeBar,
        &:focus-within HorizontalResizeBar {
            border-left: outer $border
        }
        &:focus VerticalResizeBar,
        &:focus-within VerticalResizeBar {
            border-top: outer $border
        }
    }
    """

    def __init__(self) -> None:
        super().__init__(classes="-hide")
        self.visible = False
        self.forced_width = None

    def compose(self) -> ComposeResult:
        yield HorizontalResizeBar(self)
        with VerticalGroup():
            tree = DOMTree("Application")
            tree.guide_depth = 1
            yield tree
            tabarea = VerticalGroup(id="tabcontentwrapper")
            with tabarea:
                yield VerticalResizeBar(tabarea)
                with TabbedContent("CSS", "ID & Classes"):
                    yield VerticalScroll(id="css")
                    # yield TextArea(
                    #     language="css",
                    #     soft_wrap=False,
                    #     tab_behavior="indent",
                    #     show_line_numbers=True,
                    #     compact=True,
                    #     placeholder="Waiting to highlight something...",
                    # )
                    with VerticalScroll(id="idandclasses"):
                        with HorizontalGroup(id="id"):
                            yield Label("ID")
                            yield Input(placeholder="No IDs")
                        with HorizontalGroup(id="classes"):
                            yield Label("Classes")
                            yield Input(placeholder="No Classes")

    def action__toggle_devtools_inspector(self) -> None:
        self.display = not self.display

    @on(events.Hide)
    def on_hide(self, _: events.Hide | None = None) -> None:
        self.forced_width = self.styles.width
        self.styles.width = 0
        self.add_class("-hide")

    async def make_tree(self) -> DOMTree:
        try:
            tree: DOMTree = self.query_one(DOMTree)
        except NoMatches:
            tree = DOMTree("Application")
            await self.mount(tree)
        tree: DOMTree = tree.clear()

        def build_textual_tree(parent_node: TreeNode, dom_node: DOMNode) -> None:
            for child in dom_node.query_children("*"):
                if child is self:
                    continue
                node_type = type(child).__name__
                label = f"[bold]{node_type}[/bold]"
                if child.id:
                    label += f' [cyan]id="{child.id}"[/cyan]'
                if child.classes:
                    label += f' [green]class="{" ".join(child.classes)}"[/green]'
                if not child.query_children("*"):
                    parent_node.add_leaf(label, data=child)
                else:
                    child_tree_node = parent_node.add(label, data=child)
                    build_textual_tree(child_tree_node, child)

        build_textual_tree(tree.root, self.app)
        return tree

    @on(events.Show)
    async def on_show(self, _: events.Show | None = None) -> None:
        self.remove_class("-hide")
        tree = await self.make_tree()
        tree.focus()
        tree.action_toggle_expand_all()
        tree.action_toggle_expand_all()
        tree.action_toggle_expand_all()
        self.styles.width = self.forced_width

    @on(DOMTree.NodeHighlighted)
    @work(exclusive=True)
    async def on_tree_node_highlighted(self, event: DOMTree.NodeHighlighted) -> None:
        css: VerticalScroll = self.query_one("#css", VerticalScroll)
        if isinstance(event.node.data, DOMNode):
            if event.node.data.id is None:
                self.query_one("#id > Input", Input).value = ""
            else:
                self.query_one("#id > Input", Input).value = event.node.data.id
            if event.node.data.id is None:
                self.query_one("#classes > Input", Input).value = ""
            else:
                self.query_one("#classes > Input", Input).value = " ".join(
                    event.node.data.classes
                )
            rules: RulesMap = event.node.data.styles._base_styles._rules
            to_mount = []
            for rule, value in rules.items():
                if isinstance(value, str):
                    to_mount.append(HorizontalGroup(Static(rule), Input(value, classes="str"), id=rule))
                elif isinstance(value, Color):
                    to_mount.append(HorizontalGroup(Static(rule), Input(value.hex, classes="color", validators=[ColorValidator()]), id=rule))
                elif isinstance(value, (VerticalLayout, HorizontalLayout, GridLayout)):
                    to_mount.append(
                        HorizontalGroup(
                            Static(rule),
                            Input(type(value).__name__.replace("Layout", ""), classes="layout", validators=[LayoutValidator()]), id=rule
                        )
                    )
                elif isinstance(value, Style):
                    to_mount.append(HorizontalGroup(Static(rule), Input(str(value), classes="str", validators=[StyleValidator()]), id=rule))
                elif isinstance(value, bool) and rule.startswith("auto"):
                    pass
                elif isinstance(value, int):
                    to_mount.append(HorizontalGroup(Static(rule), Input(str(value), classes="int", validators=[Number()]), id=rule))
                else:
                    print(rule, value, type(value))
            async with self.batch():
                try:
                    for rule_widget in to_mount:
                        if (input_widget := self.query_one(f"#css #{rule_widget.id} Input")):
                            input_widget.value = rule_widget.query_one(Input).value
                except NoMatches:
                    await css.remove_children()
                    await css.mount_all(to_mount)
        else:
            css.remove_children()
