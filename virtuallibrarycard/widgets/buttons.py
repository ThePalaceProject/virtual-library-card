from typing import Any

from django import forms


class FormButtonInput(forms.widgets.Input):
    """A button input, optionally wrapped in an <a> element"""

    input_type: str = "button"
    template_name: str = "form_button_input.html"
    href: str = None

    def get_context(self, name: str, value, attrs) -> dict[str, Any]:
        ctx = super().get_context(name, value, attrs)
        ctx["widget"]["href"] = self.href
        return ctx


class ButtonField(forms.Field):
    widget = FormButtonInput


class LinkButtonField(ButtonField):
    """A field with a button wrapped in an <a> tag"""

    def __init__(self, button_href, **kwargs) -> None:
        super().__init__(**kwargs)
        self.widget.href = button_href
        self.required = False
