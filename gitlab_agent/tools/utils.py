import re

from gitlab_agent.gitlab_client import GitLabClient


def _meaningful_alias_words(value: str) -> set[str]:
    """
    Splits the string on non alpanumeric characters
    e.g. "test-api" -> [test, api]
    """
    normalized = re.sub(r"[^a-z0-9]+", " ", value.lower()).split()
    return set(filter(lambda word: len(word) >= 3, normalized)) # Filter out any strings with len < 3

def _best_project_alias_match(
    user_message: str,
    project_aliases: dict[str, dict[str, str | set[str]]],
) -> tuple[str, str] | None:
    """Return the best project match using simple word overlap.
    Steps:
    1. Split the user message only on spaces and lowercase it.
       Example: "Open billing-dashboard now" -> {"open", "billing-dashboard", "now"}
    2. Ignore weak words and short words.
       Example: "api", "web", and words shorter than 3 chars are skipped.
    3. Match if any remaining user word exists in the project name words.
       Example: "open dashboard backlog" matches "billing-dashboard" via "dashboard".
    """
    message_words = _meaningful_alias_words(user_message)

    for project_name, project_data in project_aliases.items():
        project_id = project_data["project_id"]
        project_words = project_data["project_words"]
        overlap_words = project_words & message_words
        if not overlap_words:
            continue
        # Found a match return
        return project_id, project_name

    return None, None



def _aliases_from_projects(gitlab: GitLabClient) -> dict[str, dict[str, str | set[str]]]:
    """
    1. Fetches all the projects
    2. Pre-compute useful words from each project name once
    3. Map each project name to its id and processed words for future matching
    e.g. { 'project_name': {'project_id': '15', 'project_words': {'project'}} }
    """
    projects = gitlab.list_projects()
    # We always want results in projects
    if not projects:
        raise RuntimeError("No projects were found pls create one or try again")
    aliases: dict[str, dict[str, str | set[str]]] = {}
    for project in projects:
        project_id = project.get("id")
        project_id = str(project_id)
        project_name = project.get("name", "").strip().lower()
        project_words = _meaningful_alias_words(project_name)
        project_words.add(project_name)
        aliases[project_name] = { "project_id": project_id, "project_words": project_words}
    return aliases
