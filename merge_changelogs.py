from pathlib import Path
import re

targets = (
    "Core",
    "Agent",
    "API",
    "CLI",
    "Docs",
)

merged_changelog = Path("CHANGELOG.md")


def get_changelog_entries(subfolder: str):
    changelog = Path(f"jobbergate-{subfolder.lower()}") / "CHANGELOG.md"
    content = changelog.read_text()

    # Split the content by the changelog entries
    split_content = re.split(r"(## .+)", content)

    # Create a dictionary where the key is the changelog entry and the value is the text between each entry
    changelog_dict = {
        split_content[i]: split_content[i + 1].strip()
        for i in range(1, len(split_content), 2)
    }

    return changelog_dict


base_changelogs = {t: get_changelog_entries(t) for t in targets}

entries = {
    entry for changelog in base_changelogs.values() for entry in changelog.keys()
}

# Create the merged changelog
with merged_changelog.open("w") as f:
    for entry in sorted(entries, reverse=True):
        f.write(entry + "\n")
        for key, value in base_changelogs.items():
            if entry in value and value[entry].strip():
                f.write(f"### {key}\n")
                f.write(value[entry] + "\n")


def replace_issue_links(issue_prefix, issue_url):
    content = merged_changelog.read_text()

    # This regex pattern finds all instances of the issue prefix surrounded by brackets
    pattern = r"\[(" + issue_prefix + "-\d+)\]"

    # This function will be used to replace each match with the hyperlink format
    def repl(match):
        issue_id = match.group(1)
        return f"([{issue_id}]({issue_url}/{issue_id}))"

    # Use re.sub to replace all matches in the content
    content = re.sub(pattern, repl, content)

    # Write the modified content back to the file
    merged_changelog.write_text(content)


replace_issue_links("ASP", "https://jira.scania.com/browse")
replace_issue_links("PENG", "https://app.clickup.com/t/18022949")
