import os
import json
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from agents.state import GraphState
from tools.utils import parse_llm_json, clean_file_contents
from dotenv import load_dotenv

load_dotenv()

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    api_key=os.getenv("GROQ_API_KEY")
)

def apply_changes(existing_content: str, changes: list) -> str:
    content = existing_content
    for change in changes:
        if change["type"] == "modify":
            find = change["find"]
            if find in content:
                content = content.replace(find, change["replace"])
            else:
                # Try stripping comments from each line and match
                def strip_comments(code):
                    lines = code.split("\n")
                    return "\n".join(
                        line.split("#")[0].rstrip() for line in lines
                    )
                
                stripped_content = strip_comments(content)
                stripped_find = strip_comments(find)
                
                if stripped_find in stripped_content:
                    # Find the original block by locating start/end lines
                    find_lines = find.split("\n")
                    content_lines = content.split("\n")
                    
                    first_line = strip_comments(find_lines[0])
                    last_line = strip_comments(find_lines[-1])
                    
                    start_idx = None
                    for i, line in enumerate(content_lines):
                        if strip_comments(line) == first_line:
                            start_idx = i
                            break
                    
                    end_idx = None
                    if start_idx is not None:
                        for i in range(start_idx, len(content_lines)):
                            if strip_comments(content_lines[i]) == last_line:
                                end_idx = i
                                break
                    
                    if start_idx is not None and end_idx is not None:
                        replace_lines = change["replace"].split("\n")
                        content_lines = content_lines[:start_idx] + replace_lines + content_lines[end_idx+1:]
                        content = "\n".join(content_lines)
                    else:
                        print(f"Warning: could not find block to replace:\n{find}")
                else:
                    print(f"Warning: could not find block to replace:\n{find}")

        elif change["type"] == "append":
            content += f"\n\n{change['content']}"
    
    return content

def code_writer_node(state: GraphState) -> GraphState:
    issue = state["issue"]
    code_reader_output = state["code_reader_output"]
    planner_output = state["planner_output"]
    file_contents = code_reader_output["file_contents"]

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a code writer agent. Given existing code and an implementation 
         plan, produce the minimal changes needed to implement the plan.
         Respond ONLY in JSON with this structure, no markdown fences:
         {{
            "changes": [
                {{
                    "path": "path/to/existing/file",
                    "type": "modify",
                    "find": "exact existing code block to replace",
                    "replace": "new code block to replace it with"
                }},
                {{
                    "path": "path/to/existing/file",
                    "type": "append",
                    "content": "new code to append at end of file"
                }},
                {{
                    "path": "path/to/new/file",
                    "type": "create",
                    "content": "full content of new file"
                }}
            ],
            "summary": "summary of all changes made"
         }}
         IMPORTANT:
         - For modify: 'find' must be the EXACT existing code string, copy it precisely
         - For append: adds new code at the end of an existing file
         - For create: creates a brand new file with full content
         - Never rewrite entire files, make surgical changes only
        """),
        ("human", """
         Issue title: {title}
         Issue body: {body}
         Plan summary: {plan}
         Steps: {steps}
         Key changes: {key_changes}
         Files to modify: {files_to_modify}
         Files to create: {files_to_create}
         Existing code: {existing_code}
        """)
    ])
    

    cleaned_contents = {}
    for path, content in file_contents.items():
        if path.endswith(".ipynb"):
            cleaned_contents[path] = clean_file_contents(content)
        else:
            cleaned_contents[path] = content

    response = prompt | llm
    result = response.invoke({
        "title": issue["title"],
        "body": issue["body"],
        "plan": planner_output["plan_summary"],
        "steps": json.dumps(planner_output["steps"]),
        "key_changes": json.dumps(planner_output["key_changes"]),
        "files_to_modify": json.dumps(planner_output["files_to_modify"]),
        "files_to_create": json.dumps(planner_output["files_to_create"]),
        "existing_code": json.dumps(cleaned_contents)
    })

    parsed = parse_llm_json(result.content)
    raw_changes = parsed["changes"]
    summary = parsed["summary"]


    for change in raw_changes:
        if change["type"] == "modify":
            path = change["path"]
            print("=== TRYING TO FIND ===")
            print(repr(change["find"]))
            print("=== IN CONTENT ===")
            print(repr(cleaned_contents.get(path, "")[:500]))
            print("=== MATCH ===")
            print(change["find"] in cleaned_contents.get(path, ""))

    # Apply changes on top of existing content
    final_files = {}
    for change in raw_changes:
        path = change["path"]

        if change["type"] == "create":
            final_files[path] = change["content"]

        elif change["type"] in ("modify", "append"):
            if path not in final_files:
                final_files[path] = cleaned_contents.get(path, "")
            final_files[path] = apply_changes(final_files[path], [change])

    # Format for commit_files
    formatted_changes = [
        {"path": path, "content": content}
        for path, content in final_files.items()
    ]

    return {
        "code_writer_output": {
            "changes": formatted_changes,
            "raw_changes": raw_changes,
            "summary": summary
        }
    }

if __name__ == "__main__":
    from tools.github_tools import get_issue, get_file_contents

    state = {
        "issue_number": 1,
        "issue": get_issue(1),
        "repo_tree": [],
        "code_reader_output": {
            "summary": "Basic unconditional GAN on MNIST",
            "relevant_files": ["GAN.ipynb"],
            "key_functions": ["Discriminator", "Generator", "training_loop"],
            "file_contents": {"GAN.ipynb": get_file_contents("GAN.ipynb")}
        },
        "planner_output": {
            "plan_summary": "Modify GAN to support conditional image generation",
            "steps": [
                "Modify Generator to accept class labels",
                "Modify Discriminator to accept class labels",
                "Update training loop to include labels"
            ],
            "files_to_modify": ["GAN.ipynb"],
            "files_to_create": ["conditional_GAN_utils.py"],
            "key_changes": [
                "Adding class labels as input to Generator and Discriminator",
                "Updating loss functions for conditional generation",
                "Modifying training loop to include class labels"
            ]
        },
        "code_writer_output": {},
        "test_writer_output": {},
        "branch_name": "",
        "pr_url": ""
    }

    result = code_writer_node(state)
    print(json.dumps(result, indent=2))
