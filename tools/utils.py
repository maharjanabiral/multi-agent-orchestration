import json

def parse_llm_json(content: str) -> dict:
    """Strip markdown fences and parse JSON"""
    content = content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    return json.loads(content.strip())

def clean_file_contents(content: str) -> str:
    """Remove [CODE] and [MARKDOWN] markers from notebook content for LLM matching"""
    content = content.replace("[CODE]\n", "")
    content = content.replace("[MARKDOWN]\n", "")
    content = content.replace("\n---\n", "\n\n")
    return content.strip()
