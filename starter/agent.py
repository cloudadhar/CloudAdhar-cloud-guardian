"""
CloudAdhar Cloud Guardian - interactive AI agent (STARTER).

  python agent.py                                   # full security + cost report
  python agent.py "Am I wasting money anywhere?"     # ask your own question
  python agent.py --chat                            # chat mode
"""
import os
import sys

from strands import Agent
from strands.models import BedrockModel

from tools import ALL_TOOLS

MODEL_ID = os.getenv("MODEL_ID", "us.amazon.nova-pro-v1:0")
REGION = os.getenv("AWS_REGION", "us-east-1")

SYSTEM_PROMPT = """You are CloudAdhar Cloud Guardian, a friendly AWS security and cost advisor for beginners.

Rules:
- Always call the tools to get real data. Never invent findings, resource names, links or dollar amounts.
- Only call the tools needed for the question (security tools for security questions, cost tools for cost questions).
- If a tool returns an empty list, say that check passed.
- Group findings by severity: CRITICAL, HIGH, MEDIUM, LOW.
- For each finding give: what it means in simple words, why it matters, the fix steps, and the console link exactly as returned by the tool.
- For cost findings, show the estimated monthly waste and the total.
- Never run or claim to have run any fix. You only have read-only access.
- End with: number of findings per severity, total estimated monthly waste, and the ONE thing to fix first.
"""


def build_agent() -> Agent:
    model = BedrockModel(model_id=MODEL_ID, region_name=REGION, temperature=0)
    return Agent(model=model, tools=ALL_TOOLS, system_prompt=SYSTEM_PROMPT)


def main() -> None:
    agent = build_agent()
    if "--chat" in sys.argv:
        print("CloudAdhar Cloud Guardian (type 'exit' to quit)\n")
        while True:
            q = input("You: ").strip()
            if q.lower() in {"exit", "quit"}:
                break
            agent(q)
            print()
        return
    agent(" ".join(sys.argv[1:]) or "Check my AWS account for security problems and wasted money. Give me a full report.")


if __name__ == "__main__":
    main()
