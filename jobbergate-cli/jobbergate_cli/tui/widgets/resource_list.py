"""
List widget for displaying resources with actions.
"""

from typing import Callable

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DataTable, Label, Static
from textual.reactive import reactive


class ResourceListWidget(Container):
    """
    A widget for displaying a list of resources with action buttons.
    """

    resource_name: reactive[str] = reactive("Resources")
    data: reactive[list] = reactive([])

    def __init__(
        self,
        resource_name: str,
        on_create: Callable | None = None,
        on_view: Callable | None = None,
        on_refresh: Callable | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.resource_name = resource_name
        self._on_create = on_create
        self._on_view = on_view
        self._on_refresh = on_refresh

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        with Vertical():
            with Horizontal(classes="header"):
                yield Label(self.resource_name, classes="title")
                if self._on_create:
                    yield Button("➕ Create New", id="btn_create", variant="success")
                if self._on_refresh:
                    yield Button("🔄 Refresh", id="btn_refresh", variant="primary")
            yield DataTable(id="resource_table", zebra_stripes=True, cursor_type="row")

    def on_mount(self) -> None:
        """Set up the data table when mounted."""
        table = self.query_one(DataTable)
        table.add_columns("ID", "Name", "Owner", "Created", "Actions")
        table.cursor_type = "row"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn_create" and self._on_create:
            self._on_create()
        elif event.button.id == "btn_refresh" and self._on_refresh:
            self._on_refresh()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection to view details."""
        if self._on_view and event.row_key:
            row_data = self.query_one(DataTable).get_row(event.row_key.value)
            if row_data:
                item_id = row_data[0]
                self._on_view(item_id)

    def update_data(self, items: list) -> None:
        """Update the table with new data."""
        table = self.query_one(DataTable)
        table.clear()
        
        for item in items:
            created = item.created_at.format("YYYY-MM-DD HH:mm") if hasattr(item.created_at, 'format') else str(item.created_at)
            table.add_row(
                str(item.id),
                item.name[:40] if len(item.name) > 40 else item.name,
                item.owner_email[:30] if len(item.owner_email) > 30 else item.owner_email,
                created,
                "👁 View",
                key=str(item.id),
            )
