# used as a replacement for textual.widgets.__init__ since it lazyloads widgets, which nuitka cannot identify.

from textual.widgets._button import Button
from textual.widgets._checkbox import Checkbox
from textual.widgets._input import Input
from textual.widgets._label import Label
from textual.widgets._loading_indicator import LoadingIndicator
from textual.widgets._option_list import OptionList
from textual.widgets._progress_bar import ProgressBar
from textual.widgets._radio_button import RadioButton
from textual.widgets._radio_set import RadioSet
from textual.widgets._select import Select
from textual.widgets._selection_list import SelectionList
from textual.widgets._static import Static
from textual.widgets._switch import Switch
from textual.widgets._tabs import Tabs
from textual.widgets._tooltip import Tooltip

__all__ = [
    "Button",
    "Checkbox",
    "Input",
    "Label",
    "LoadingIndicator",
    "OptionList",
    "ProgressBar",
    "RadioButton",
    "RadioSet",
    "Select",
    "SelectionList",
    "Static",
    "Switch",
    "Tabs",
    "Tooltip",
]
