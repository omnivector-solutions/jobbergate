# Comprehensive TUI Demo Application

This application showcases **all** Jobbergate question types and the new Textual TUI interface.

## Features Demonstrated

### Question Types
1. **Text** - Simple text input (with and without defaults)
2. **Integer** - Numeric input with min/max validation
3. **List** - Dropdown/select from choices
4. **Checkbox** - Multi-select checkboxes
5. **Confirm** - Yes/No boolean question
6. **BooleanList** - Conditional questions based on yes/no answer
7. **Directory** - Directory path input

### TUI Features
- ✅ **Green borders** for valid inputs with defaults
- ✅ **Red borders** for invalid inputs (try entering 0 or 101 for num_nodes)
- ⚪ **Neutral** for empty optional fields
- 🔄 **Real-time validation** as you type
- ❌ **Error modal** when clicking Continue with invalid fields
- 🚫 **Cancel button** to abort without creating job script
- 📋 **Multiple workflows** - questions are organized in logical groups

## How to Use

### With TUI (Textual Interface)
```bash
jobbergate job-scripts create-locally . --tui
```

### With Traditional CLI (Inquirer)
```bash
jobbergate job-scripts create-locally .
```

## Workflow Structure

### 1. Main Flow
- Job name (with default: "my-awesome-job")
- Description (optional, no default)
- Number of nodes (1-100, default: 4)
- Number of tasks (1-48, **no default** - try leaving empty then Continue to see error!)
- Partition selection (dropdown, default: "standard")

### 2. Advanced Flow
- Software modules (multi-select checkboxes, default: python/3.11)
- Email notifications (yes/no switch, default: Yes)
- GPU usage (conditional questions):
  - If YES: asks for number of GPUs and GPU type
  - If NO: asks for CPU architecture preference

### 3. Final Flow
- Working directory (dynamic default based on job name)
- Walltime hours (1-72, default: 2)
- Output filename (dynamic default based on job name)

## Testing Validation

Try these to see the TUI validation in action:

1. **Leave `num_tasks` empty** and click Continue → Error modal appears
2. **Enter `0` or `101` for `num_nodes`** → Red border + error on Continue
3. **Enter valid values** → Green borders immediately
4. **Toggle `use_gpu` switch** → Watch conditional questions appear/disappear
5. **Click Cancel** → Operation aborts, no job script created
6. **Fill valid values and Continue** → Success! Job script created

## What to Observe

When the TUI loads:
- Fields with **valid defaults show GREEN** immediately
- Fields **without defaults are neutral** (no color)
- As you type, fields update to **GREEN** (valid) or **RED** (invalid)
- Empty required fields only show errors when you click Continue
