import contextlib

from rich.style import Style
from rich.text import TextType
from textual import events, on
from textual.app import ComposeResult
from textual.color import Color
from textual.containers import HorizontalGroup, VerticalGroup, VerticalScroll
from textual.css.query import NoMatches
from textual.css.scalar import Scalar
from textual.css.styles import RulesMap
from textual.dom import DOMNode
from textual.geometry import Spacing
from textual.layouts.grid import GridLayout
from textual.layouts.horizontal import HorizontalLayout
from textual.layouts.vertical import VerticalLayout
from textual.validation import Number
from textual.widgets import Input, Label, Static, TabbedContent, Tree
from textual.widgets.tree import TreeDataType, TreeNode

from rovr.resizebar import HorizontalResizeBar, VerticalResizeBar
from rovr.validators import (
    BorderValidator,
    CheckID,
    ColorValidator,
    FloatValidator,
    LayoutValidator,
    ScalarValidator,
    SpacingValidator,
    StyleValidator,
)


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
        self.prev_hovered_index = -1


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
                width: 1fr;
                background: transparent !important
            }
            Static {
                width: auto;
                text-wrap: nowrap;
                text-overflow: ellipsis;
            }
            Static#filler {
                width: 2;
                text-overflow: clip;
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
                            yield Input(
                                placeholder="No IDs",
                                validators=[CheckID()],
                                validate_on=["changed"],
                                valid_empty=True
                            )
                        with HorizontalGroup(id="classes"):
                            yield Label("Classes")
                            yield Input(
                                placeholder="No Classes", validate_on=["changed"], valid_empty=True
                            )

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
    async def on_tree_node_highlighted(self, event: DOMTree.NodeHighlighted) -> None:
        css: VerticalScroll = self.query_one("#css", VerticalScroll)
        await css.remove_children()
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
            rules: RulesMap = event.node.data.styles.base._rules | event.node.data.styles.inline._rules
            to_mount = []
            for rule, value in rules.items():
                input_widget: Input | None = None
                if isinstance(value, str):
                    input_widget = Input(value, classes="str")
                elif isinstance(value, Color):
                    input_widget = Input(
                        value.hex,
                        classes="color",
                        validators=[ColorValidator()],
                    )
                elif isinstance(value, (VerticalLayout, HorizontalLayout, GridLayout)):
                    input_widget = Input(
                        type(value).__name__.replace("Layout", "").lower(),
                        classes="layout",
                        validators=[LayoutValidator()],
                    )
                elif isinstance(value, Style):
                    input_widget = Input(
                        str(value),
                        classes="style",
                        validators=[StyleValidator()],
                    )
                elif isinstance(value, bool) and rule.startswith("auto"):
                    pass
                elif isinstance(value, int):
                    input_widget = Input(
                        str(value),
                        classes="int",
                        validators=[Number(failure_description="Must be a number!")],
                    )
                elif isinstance(value, float):
                    input_widget = Input(
                        str(value),
                        classes="float",
                        validators=[FloatValidator()],
                    )
                elif isinstance(value, Scalar):
                    input_widget = Input(
                        str(value),
                        classes="scalar",
                        validators=[ScalarValidator()],
                    )
                elif isinstance(value, Spacing):
                    input_widget = Input(
                        value.css,
                        classes="spacing",
                        validators=[SpacingValidator()],
                    )
                elif isinstance(value, tuple):
                    if rule.startswith("border"):
                        input_widget = Input(
                            f"{value[0]} {value[1].hex}",
                            classes="tuple-border",
                            validators=[BorderValidator("border")]
                        )
                    else:
                        self.notify(str((rule, value, type(value))), timeout=3)
                else:
                    self.notify(str((rule, value, type(value))), timeout=3)
                if input_widget is not None:
                    input_widget.validate_on = {"changed"}
                    to_mount.append(
                        HorizontalGroup(
                            Static(rule), Static(": ", classes="filler"), input_widget, id=rule
                        )
                    )
            await css.mount_all(to_mount)

    @on(Input.Changed, "#id > Input")
    @on(Input.Changed, "#classes > Input")
    def update_class_or_id(self, event: Input.Changed) -> None:
        assert event.input.parent is not None
        domtree: DOMTree = self.query_one(DOMTree)
        if domtree.cursor_node is None or not event.input.is_valid:
            return
        if not isinstance(domtree.cursor_node.data, DOMNode):
            return
        if event.input.parent.id == "id":
            domtree.cursor_node.data._nodes.updated()
            domtree.cursor_node.data._id = event.value
        elif event.input.parent.id == "classes":
            domtree.cursor_node.data.classes = frozenset(event.value.split())

    @on(Input.Changed, "#css Input")
    def update_style(self, event: Input.Changed) -> None:
        assert isinstance(event.input.parent, HorizontalGroup)
        domtree: DOMTree = self.query_one(DOMTree)
        if domtree.cursor_node is None:
            return
        if val := event.input.validate(event.value):  # noqa: SIM102
            if val is not None and val.failures:
                return
        if not isinstance(domtree.cursor_node.data, DOMNode):
            return
        with contextlib.suppress(KeyError):
            to_set_value = None
            if event.input.has_class("int"):
                to_set_value = int(event.value)
            elif event.input.has_class("float"):
                to_set_value = float(event.value)
            elif event.input.has_class("color"):
                to_set_value = Color.parse(event.value)
            elif event.input.has_class("layout"):
                if event.value == "vertical":
                    to_set_value = VerticalLayout()
                elif event.value == "horizontal":
                    to_set_value = HorizontalLayout()
                elif event.value == "grid":
                    to_set_value = GridLayout()
                else:
                    return
            elif event.input.has_class("style"):
                to_set_value = Style.parse(event.value)
            elif event.input.has_class("scalar"):
                to_set_value = Scalar.parse(event.value)
            elif event.input.has_class("spacing"):
                to_set_value = Spacing.unpack(list(map(lambda x: int(float(x)), event.value.split())))
            elif event.input.has_class("tuple-border"):
                splitted = event.value.split()
                to_set_value = (splitted[0], Color.parse(splitted[1]))
            domtree.cursor_node.data.styles.__dict__[event.input.parent.id] = to_set_value

    @on(events.MouseMove)
    async def on_mouse_move(self, event: events.MouseMove) -> None:
        if isinstance(event.widget, DOMTree) and event.widget.hover_line != -1:
            node = event.widget.get_node_at_line(event.widget.hover_line)
            if node is not None and isinstance(node.data, DOMNode):
                async with self.batch():
                    if event.widget.prev_hovered_index != -1:
                        prev_hovered_node = event.widget.get_node_at_line(
                            event.widget.prev_hovered_index
                        )
                        if prev_hovered_node is not None and isinstance(
                            prev_hovered_node.data, DOMNode
                        ):
                            if prev_hovered_node.data is node.data:
                                return
                            prev_hovered_node.data.remove_class("-highlight")
                    node.data.add_class("-highlight")
                    event.widget.prev_hovered_index = event.widget.hover_line

    @on(events.Leave)
    def on_mouse_leave(self, event: events.Leave) -> None:
        domtree: DOMTree = self.query_one(DOMTree)
        if domtree.prev_hovered_index != -1 and hasattr(node := domtree.get_node_at_line(domtree.prev_hovered_index), "data"):
            node.data.remove_class("-highlight")
