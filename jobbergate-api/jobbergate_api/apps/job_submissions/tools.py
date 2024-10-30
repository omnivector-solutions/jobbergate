import re


def get_cloned_description(original_description: str, original_job_submission_id: int) -> str:
    """
    Add the appropriate cloned from ID to the description of a cloned job submission.

    If the original description already contains a cloned ID, it will be replaced with the new one.
    If the original description is empty, only the cloned ID will be returned.

    Args:
        original_description (str): The original job submission description.
        original_job_submission_id (int): The ID of the original job submission.

    Returns:
        str: The updated job submission description with the cloned ID.
    """
    pattern = re.compile(r"\[cloned from ID \d+\]$")
    replacement = f"[cloned from ID {original_job_submission_id}]"
    result = pattern.sub("", original_description).strip()
    return f"{result} {replacement}" if result else replacement
