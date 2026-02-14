"""
Main TUI application for Jobbergate CLI.
"""

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Footer, Header, TabbedContent, TabPane, LoadingIndicator
from textual.binding import Binding
from textual.worker import Worker, WorkerState

from jobbergate_core.sdk import Apps
from jobbergate_cli.tui.widgets.resource_list import ResourceListWidget
from jobbergate_cli.tui.screens.detail import ResourceDetailScreen


class JobbergateTUI(App):
    """
    A Textual TUI for managing Jobbergate resources.
    """

    CSS = """
    Screen {
        background: $surface;
    }

    .header {
        height: 3;
        padding: 1;
        background: $primary;
        border: solid $accent;
    }

    .title {
        width: 1fr;
        content-align: center middle;
        text-style: bold;
        color: $text;
    }

    #detail_container {
        padding: 2;
        height: 100%;
    }

    .detail_title {
        text-style: bold;
        text-align: center;
        padding: 1;
        background: $primary;
        color: $text;
        margin-bottom: 1;
    }

    #detail_content {
        padding: 2;
        height: 1fr;
        overflow-y: auto;
        border: solid $accent;
        margin-bottom: 1;
    }

    .action_buttons {
        height: auto;
        padding: 1;
        align: center middle;
        dock: bottom;
    }

    DataTable {
        height: 1fr;
        border: solid $accent;
    }

    Button {
        margin: 0 1;
        min-width: 15;
    }

    TabbedContent {
        height: 1fr;
    }

    TabPane {
        padding: 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("1", "switch_tab('templates')", "Templates", show=True),
        Binding("2", "switch_tab('scripts')", "Scripts", show=True),
        Binding("3", "switch_tab('submissions')", "Submissions", show=True),
        Binding("?", "help", "Help", show=True),
    ]

    def __init__(self, sdk: Apps):
        super().__init__()
        self.sdk = sdk
        self.title = "Jobbergate TUI"
        self.sub_title = "Manage Applications, Scripts & Submissions"

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()
        with TabbedContent(initial="templates"):
            with TabPane("Applications", id="templates"):
                yield ResourceListWidget(
                    "Job Templates (Applications)",
                    on_create=self.create_template,
                    on_view=self.view_template,
                    on_refresh=self.refresh_templates,
                    id="templates_list",
                )
            with TabPane("Job Scripts", id="scripts"):
                yield ResourceListWidget(
                    "Job Scripts",
                    on_create=self.create_script,
                    on_view=self.view_script,
                    on_refresh=self.refresh_scripts,
                    id="scripts_list",
                )
            with TabPane("Job Submissions", id="submissions"):
                yield ResourceListWidget(
                    "Job Submissions",
                    on_create=self.create_submission,
                    on_view=self.view_submission,
                    on_refresh=self.refresh_submissions,
                    id="submissions_list",
                )
        yield Footer()

    def on_mount(self) -> None:
        """Load initial data when app mounts."""
        self.call_later(self.refresh_templates)

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        """Load data when tab is activated."""
        if event.pane.id == "templates" and not self.query_one("#templates_list", ResourceListWidget).data:
            self.refresh_templates()
        elif event.pane.id == "scripts" and not self.query_one("#scripts_list", ResourceListWidget).data:
            self.refresh_scripts()
        elif event.pane.id == "submissions" and not self.query_one("#submissions_list", ResourceListWidget).data:
            self.refresh_submissions()

    def action_refresh(self) -> None:
        """Refresh the current tab's data."""
        active_pane = self.query_one(TabbedContent).active
        if active_pane == "templates":
            self.refresh_templates()
        elif active_pane == "scripts":
            self.refresh_scripts()
        elif active_pane == "submissions":
            self.refresh_submissions()

    def action_switch_tab(self, tab_id: str) -> None:
        """Switch to a specific tab."""
        tabbed = self.query_one(TabbedContent)
        tabbed.active = tab_id
        self.action_refresh()

    def action_help(self) -> None:
        """Show help information."""
        help_text = """
[bold]Jobbergate TUI - Keyboard Shortcuts[/bold]

[yellow]Navigation:[/yellow]
  1, 2, 3     - Switch between tabs
  ↑/↓ or j/k  - Navigate list items
  Enter       - View selected item details
  Escape      - Go back / Close detail view

[yellow]Actions:[/yellow]
  r           - Refresh current view
  q           - Quit application
  ?           - Show this help

[yellow]In List Views:[/yellow]
  Use buttons or select row and press Enter to view details

[yellow]In Detail Views:[/yellow]
  Use buttons to perform actions (Edit, Clone, Delete, etc.)
  Escape to return to list view
"""
        self.notify(help_text, title="Help", timeout=15)

    def refresh_templates(self) -> None:
        """Load job templates from SDK."""
        try:
            self.notify("Loading templates...", timeout=2)
            response = self.sdk.job_templates.get_list()
            templates = response.items
            list_widget = self.query_one("#templates_list", ResourceListWidget)
            list_widget.update_data(templates)
            self.notify(f"✓ Loaded {len(templates)} job templates", timeout=3)
        except Exception as e:
            self.notify(f"Error loading templates: {str(e)}", severity="error", timeout=10)

    def refresh_scripts(self) -> None:
        """Load job scripts from SDK."""
        try:
            self.notify("Loading job scripts...", timeout=2)
            response = self.sdk.job_scripts.get_list()
            scripts = response.items
            list_widget = self.query_one("#scripts_list", ResourceListWidget)
            list_widget.update_data(scripts)
            self.notify(f"✓ Loaded {len(scripts)} job scripts", timeout=3)
        except Exception as e:
            self.notify(f"Error loading scripts: {str(e)}", severity="error", timeout=10)

    def refresh_submissions(self) -> None:
        """Load job submissions from SDK."""
        try:
            self.notify("Loading submissions...", timeout=2)
            response = self.sdk.job_submissions.get_list()
            submissions = response.items
            list_widget = self.query_one("#submissions_list", ResourceListWidget)
            list_widget.update_data(submissions)
            self.notify(f"✓ Loaded {len(submissions)} job submissions", timeout=3)
        except Exception as e:
            self.notify(f"Error loading submissions: {str(e)}", severity="error", timeout=10)

    def view_template(self, template_id: str) -> None:
        """View template details."""
        try:
            template = self.sdk.job_templates.get_one(int(template_id))
            detail_data = {
                "id": template.id,
                "name": template.name,
                "identifier": template.identifier,
                "owner_email": template.owner_email,
                "description": template.description,
                "created_at": template.created_at.format("YYYY-MM-DD HH:mm:ss"),
                "updated_at": template.updated_at.format("YYYY-MM-DD HH:mm:ss"),
                "is_archived": template.is_archived,
                "cloned_from_id": template.cloned_from_id,
            }
            screen = ResourceDetailScreen(
                "Job Template",
                detail_data,
                on_update=self.update_template,
                on_delete=self.delete_template,
                on_clone=self.clone_template,
                on_create_from=self.create_script_from_template,
                create_from_label="Create Job Script",
            )
            self.push_screen(screen)
        except Exception as e:
            self.notify(f"Error viewing template: {str(e)}", severity="error")

    def view_script(self, script_id: str) -> None:
        """View script details."""
        try:
            script = self.sdk.job_scripts.get_one(int(script_id))
            detail_data = {
                "id": script.id,
                "name": script.name,
                "owner_email": script.owner_email,
                "description": script.description,
                "created_at": script.created_at.format("YYYY-MM-DD HH:mm:ss"),
                "updated_at": script.updated_at.format("YYYY-MM-DD HH:mm:ss"),
                "is_archived": script.is_archived,
                "parent_template_id": script.parent_template_id,
                "cloned_from_id": script.cloned_from_id,
            }
            screen = ResourceDetailScreen(
                "Job Script",
                detail_data,
                on_update=self.update_script,
                on_delete=self.delete_script,
                on_clone=self.clone_script,
                on_create_from=self.create_submission_from_script,
                create_from_label="Create Submission",
            )
            self.push_screen(screen)
        except Exception as e:
            self.notify(f"Error viewing script: {str(e)}", severity="error")

    def view_submission(self, submission_id: str) -> None:
        """View submission details."""
        try:
            submission = self.sdk.job_submissions.get_one(int(submission_id))
            detail_data = {
                "id": submission.id,
                "name": submission.name,
                "owner_email": submission.owner_email,
                "description": submission.description,
                "created_at": submission.created_at.format("YYYY-MM-DD HH:mm:ss"),
                "updated_at": submission.updated_at.format("YYYY-MM-DD HH:mm:ss"),
                "is_archived": submission.is_archived,
                "job_script_id": submission.job_script_id,
                "slurm_job_id": submission.slurm_job_id,
                "client_id": submission.client_id,
                "status": submission.status,
                "slurm_job_state": submission.slurm_job_state,
                "cloned_from_id": submission.cloned_from_id,
            }
            screen = ResourceDetailScreen(
                "Job Submission",
                detail_data,
                on_delete=self.delete_submission,
                on_clone=self.clone_submission,
            )
            self.push_screen(screen)
        except Exception as e:
            self.notify(f"Error viewing submission: {str(e)}", severity="error")

    def create_template(self) -> None:
        """Create a new job template."""
        self.notify("Create template not yet implemented", severity="warning")

    def update_template(self, template_id: int) -> None:
        """Update a job template."""
        self.notify(f"Update template {template_id} not yet implemented", severity="warning")

    def delete_template(self, template_id: int) -> None:
        """Delete a job template."""
        try:
            self.sdk.job_templates.delete(template_id)
            self.notify(f"Deleted template {template_id}")
            self.app.pop_screen()
            self.refresh_templates()
        except Exception as e:
            self.notify(f"Error deleting template: {str(e)}", severity="error")

    def clone_template(self, template_id: int) -> None:
        """Clone a job template."""
        try:
            cloned = self.sdk.job_templates.clone(template_id)
            self.notify(f"Cloned template as {cloned.name}")
            self.app.pop_screen()
            self.refresh_templates()
        except Exception as e:
            self.notify(f"Error cloning template: {str(e)}", severity="error")

    def create_script(self) -> None:
        """Create a new job script."""
        self.notify("Create script not yet implemented", severity="warning")

    def create_script_from_template(self, template_id: int) -> None:
        """Create a job script from a template."""
        self.notify(f"Create script from template {template_id} not yet implemented", severity="warning")

    def update_script(self, script_id: int) -> None:
        """Update a job script."""
        self.notify(f"Update script {script_id} not yet implemented", severity="warning")

    def delete_script(self, script_id: int) -> None:
        """Delete a job script."""
        try:
            self.sdk.job_scripts.delete(script_id)
            self.notify(f"Deleted script {script_id}")
            self.app.pop_screen()
            self.refresh_scripts()
        except Exception as e:
            self.notify(f"Error deleting script: {str(e)}", severity="error")

    def clone_script(self, script_id: int) -> None:
        """Clone a job script."""
        try:
            cloned = self.sdk.job_scripts.clone(script_id)
            self.notify(f"Cloned script as {cloned.name}")
            self.app.pop_screen()
            self.refresh_scripts()
        except Exception as e:
            self.notify(f"Error cloning script: {str(e)}", severity="error")

    def create_submission(self) -> None:
        """Create a new job submission."""
        self.notify("Create submission not yet implemented", severity="warning")

    def create_submission_from_script(self, script_id: int) -> None:
        """Create a job submission from a script."""
        self.notify(f"Create submission from script {script_id} not yet implemented", severity="warning")

    def delete_submission(self, submission_id: int) -> None:
        """Delete a job submission."""
        try:
            self.sdk.job_submissions.delete(submission_id)
            self.notify(f"Deleted submission {submission_id}")
            self.app.pop_screen()
            self.refresh_submissions()
        except Exception as e:
            self.notify(f"Error deleting submission: {str(e)}", severity="error")

    def clone_submission(self, submission_id: int) -> None:
        """Clone a job submission."""
        try:
            cloned = self.sdk.job_submissions.clone(submission_id)
            self.notify(f"Cloned submission as {cloned.name}")
            self.app.pop_screen()
            self.refresh_submissions()
        except Exception as e:
            self.notify(f"Error cloning submission: {str(e)}", severity="error")
