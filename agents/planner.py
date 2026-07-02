import os
import json
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from agents.state import GraphState
from dotenv import load_dotenv

load_dotenv()

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY")
)

def planner_node(state: GraphState) -> GraphState:
    issue = state["issue"]
    code_reader_output = state["code_reader_output"]

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a planning agent. Given a GitHub issue and a summary of the 
         existing codebase, produce a detailed implementation plan.
         Respond ONLY in JSON with this structure, no markdown fences:
         {{
            "plan_summary": "brief summary of the approach",
            "steps": ["step ", "step 2", ...],
            "files_to_modify": ["path/to/file"],
            "files_to_create": ["path/to/new/file"],
            "key_changes": ["describe each key change needed"]
         }}
        """),
        ("human", """
         Issue title: {title}
         Issue body: {body}
         Code summary: {summary}
         Relevant files: {relevant_files}
         Key functions: {key_functions}
        """)
    ])

    response = prompt | llm
    result = response.invoke({
        "title": issue["title"],
        "body": issue["body"],
        "summary": code_reader_output["summary"],
        "relevant_files": json.dumps(code_reader_output["relevant_files"]),
        "key_functions": json.dumps(code_reader_output["key_functions"])
    })

    return {
        "planner_output": json.loads(result.content)
    }

if __name__ == "__main__":
    from tools.github_tools import get_issue

    state = {
        "issue_number": 1,
        "issue": get_issue(1),
        "repo_tree": [],
        "code_reader_output": {
            "summary": "Basic unconditional GAN on MNIST",
            "relevant_files": ["GAN.ipynb"],
            "key_functions": ["Discriminator", "Generator", "training_loop"],
            "file_contents": {}
        },
        "planner_output": {},
        "code_writer_output": {},
        "test_writer_output": {},
        "branch_name": "",
        "pr_url": ""
    }

    result = planner_node(state)
    print(json.dumps(result, indent=2))
