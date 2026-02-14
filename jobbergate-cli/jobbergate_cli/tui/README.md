# Jobbergate TUI (Terminal User Interface)

A Textual-powered interactive terminal interface for managing Jobbergate resources.

## Features

### Three Main Views (Tabs)
1. **Applications (Job Templates)** - Manage job templates
2. **Job Scripts** - Manage job scripts created from templates
3. **Job Submissions** - Manage job submissions to the cluster

### Capabilities
- ✅ **List** all resources with pagination
- ✅ **View** detailed information for each resource
- ✅ **Delete** resources
- ✅ **Clone** existing resources
- ✅ **Create** job scripts from templates
- ✅ **Create** job submissions from scripts
- 🚧 **Create** new resources (templates/scripts/submissions) - Coming soon
- 🚧 **Edit** existing resources - Coming soon

## Usage

Launch the TUI from the command line:

```bash
jobbergate tui
```

You must be logged in first:

```bash
jobbergate login
jobbergate tui
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `1`, `2`, `3` | Switch between tabs (Templates, Scripts, Submissions) |
| `↑` / `↓` or `j` / `k` | Navigate list items |
| `Enter` | View selected item details |
| `Escape` | Go back / Close detail view |
| `r` | Refresh current view |
| `q` | Quit application |
| `?` | Show help |

## Navigation

### In List Views
- Use arrow keys to navigate through items
- Press `Enter` or click a row to view details
- Click "Create New" button to create new resources
- Click "Refresh" button to reload data

### In Detail Views
- Use action buttons to:
  - **Edit** - Modify the resource (coming soon)
  - **Clone** - Create a copy of the resource
  - **Delete** - Remove the resource
  - **Create Job Script** (templates only) - Generate a script from this template
  - **Create Submission** (scripts only) - Submit this script as a job
- Press `Escape` or click "Back" to return to list

## Architecture

```
jobbergate_cli/tui/
├── __init__.py           # Package exports
├── app.py                # Main TUI application with tabs
├── screens/
│   ├── __init__.py
│   └── detail.py         # Detail view screen for individual resources
└── widgets/
    ├── __init__.py
    └── resource_list.py  # List widget for displaying resources
```

## SDK Integration

The TUI directly uses the `jobbergate-core` SDK:
- `Apps.job_templates.get_list()` - List templates
- `Apps.job_templates.get_one(id)` - Get template details
- `Apps.job_scripts.get_list()` - List scripts
- `Apps.job_scripts.get_one(id)` - Get script details
- `Apps.job_submissions.get_list()` - List submissions
- `Apps.job_submissions.get_one(id)` - Get submission details
- Delete and clone methods for all resources

All API calls go through the authenticated SDK client, using the same authentication context as the CLI.

## Error Handling

- Network errors and API failures are displayed as notifications
- Authentication errors redirect to login
- All operations provide user feedback via notifications

## Styling

The TUI uses Textual's built-in themes and styling system:
- Dark mode by default
- Color-coded action buttons (success=green, error=red, primary=blue)
- Bordered tables and panels for clear visual separation
- Icons in buttons and list items for visual clarity
