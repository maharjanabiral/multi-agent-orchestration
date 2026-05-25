from typing import TypedDict

class GraphState(TypedDict):
    issue_number: int
    issue: dict
    repo_tree: list
    code_reader_output: dict
    planner_output: dict
    code_writer_output: dict
    test_writer_output: dict
    pr_url: str
    branch_name: str

