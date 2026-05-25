from github import Auth, Github, GithubIntegration
import json
from dotenv import load_dotenv
import os

AUTH_TOKEN = os.getenv("AUTH_TOKEN")

auth = Auth.Token(AUTH_TOKEN)
g = Github(auth=auth)

repo = g.get_repo(f"{g.get_user().login}/unconditional-mnist-gan")

def get_repo_tree():
    
    """Recursively get all file paths in the repo"""
    all_files = []
    contents = repo.get_contents("")
    
    while contents:
        file_content = contents.pop(0)
        if file_content.type == "dir":
            contents.extend(repo.get_contents(file_content.path))
        else:
            all_files.append(file_content.path)
    
    return all_files


def get_file_contents(file_path: str):
    file = repo.get_contents(file_path)
    raw = file.decoded_content.decode('utf-8')

    if file_path.endswith(".ipynb"):
        notebook = json.loads(raw)
        cells = []
        for cell in notebook["cells"]:
            cell_type = cell["cell_type"]
            source = "".join(cell["source"])
            cells.append(f"[{cell_type.upper()}]\n{source}")
        return "\n\n---\n\n".join(cells)
    
    return raw


def get_issue(issue_number: int):

    issue = repo.get_issue(number=issue_number)

    return {
        "number": issue_number,
        "title": issue.title,
        "body": issue.body,
        "labels": [label.name for label in issue.labels],
        "comments": [comment.body for comment in issue.get_comments()]
    }

def create_branch(issue_number: int):
    issue = get_issue(issue_number)
    branch_name = f"fix-issue-{issue['number']}-{issue['title'][:30].lower().replace(' ', '-')}"
    source_branch = repo.get_branch("main")
    repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=source_branch.commit.sha)
    


if __name__ == "__main__":
    create_branch()
