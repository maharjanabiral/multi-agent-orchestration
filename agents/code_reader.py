import os
import json
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from agents.state import GraphState
from tools.github_tools import get_repo_tree, get_file_contents 
from dotenv import load_dotenv

load_dotenv()
GROQ_API_KEY=os.getenv("GROQ_API_KEY")

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=GROQ_API_KEY
)

def code_reader_node(state: GraphState) -> GraphState:
    
    issue = state["issue"]
    tree = get_repo_tree()

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a code reader agent. Given a GitHub issue and a list of files in the repo,
         identify which files are most relevant to the issue.
         Respond ONLY in JSON with this structure, no markdown fences:
         {{"relevant_files": ["path/to/file1", "path/to/file2"]}}
        """),
        ("human", """
         Issue title: {title}
         Issue body: {body}
         Repo files: {tree}
        """)
    ])

    chain = prompt | llm
    result = chain.invoke({
        "title": issue["title"],
        "body": issue["body"],
        "tree": json.dumps(tree)
    })

    relevant_files = json.loads(result.content)["relevant_files"]

    file_contents = {}
    for path in relevant_files:
        file_contents[path] = get_file_contents(path)

    summary_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a code reader agent. Summarize the relevant code for the given issue.
         Respond ONLY in JSON with this structure, no markdown fences:
         {{
            "summary": "overall summary of relevant code",
            "relevant_files": ["list of file paths"],
            "key_functions": ["list of key functions or classes relevant to the issue"]
         }}
        """),
        ("human", """
         Issue: {issue}
         File contents: {file_contents}
        """)
    ])

    summary_response = summary_prompt | llm
    summary = summary_response.invoke({
        "issue": json.dumps(issue),
        "file_contents": json.dumps(file_contents)
    })

    return {
        "repo_tree": tree,
        "code_reader_output": {
            **json.loads(summary.content),
            "file_contents": file_contents
        }
    }

if __name__ == "__main__":
    from tools.github_tools import get_issue

    state = {
        "issue_number": 1,
        "issue": get_issue(1),
        "repo_tree": [],
        "code_reader_output": {},
        "planner_output": {},
        "code_writer_output": {},
        "test_writer_output": {},
        "branch_name": "",
        "pr_url": ""
    }

    result = code_reader_node(state)
    print(result)
