"""
Detail view screen for displaying and managing a single resource.
"""

from typing import Callable

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Header, Footer, Label, Static


class ResourceDetailScreen(Screen):
    """
    A screen for displaying and managing resource details.
    """

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
    ]

    def __init__(
        self,
        resource_name: str,
        resource_data: dict,
        on_update: Callable | None = None,
        on_delete: Callable | None = None,
        on_clone: Callable | None = None,
        on_create_from: Callable | None = None,
        create_from_label: str | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.resource_name = resource_name
        self.resource_data = resource_data
        self._on_update = on_update
        self._on_delete = on_delete
        self._on_clone = on_clone
        self._on_create_from = on_create_from
        self._create_from_label = create_from_label

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()
        with Container(id="detail_container"):
            with Vertical():
                yield Label(f"{self.resource_name} Details", classes="detail_title")
                yield Static(self._format_details(), id="detail_content")
                with Horizontal(classes="action_buttons"):
                    if self._on_update:
                        yield Button("✏️  Edit", id="btn_update", variant="primary")
                    if self._on_clone:
                        yield Button("📋 Clone", id="btn_clone", variant="primary")
                    if self._on_create_from and self._create_from_label:
                        yield Button(f"➕ {self._create_from_label}", id="btn_create_from", variant="success")
                    if self._on_delete:
                        yield Button("🗑️  Delete", id="btn_delete", variant="error")
                    yield Button("⬅️  Back", id="btn_back")
        yield Footer()

    def _format_details(self) -> str:
        """Format resource data for display."""
        lines = []
        for key, value in self.resource_data.items():
            if value is not None:
                if isinstance(value, dict):
                    lines.append(f"[bold]{key}:[/bold]")
                    for k, v in value.items():
                        lines.append(f"  {k}: {v}")
                elif isinstance(value, list):
                    lines.append(f"[bold]{key}:[/bold] {len(value)} items")
                else:
                    lines.append(f"[bold]{key}:[/bold] {value}")
        return "\n".join(lines)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn_back":
            self.app.pop_screen()
        elif event.button.id == "btn_update" and self._on_update:
            self._on_update(self.resource_data.get("id"))
        elif event.button.id == "btn_delete" and self._on_delete:
            self._on_delete(self.resource_data.get("id"))
        elif event.button.id == "btn_clone" and self._on_clone:
            self._on_clone(self.resource_data.get("id"))
        elif event.button.id == "btn_create_from" and self._on_create_from:
            self._on_create_from(self.resource_data.get("id"))
