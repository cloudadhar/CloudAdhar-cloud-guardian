"""
Run this first:  python check_setup.py

It checks that your environment is ready for the workshop (CloudAdhar Cloud Guardian):
1. Python version
2. Libraries installed
3. AWS login works
4. Amazon Bedrock model access works
"""
import os
import sys

REGION = os.getenv("AWS_REGION", "us-east-1")
# Nova Pro is called through an inference profile named after your region group: us., eu. or apac.
PROFILE = {"us": "us", "eu": "eu", "ap": "apac"}.get(REGION.split("-")[0], "us")
MODEL_ID = os.getenv("MODEL_ID", f"{PROFILE}.amazon.nova-pro-v1:0")
ok = True


def step(name, passed, help_text=""):
    global ok
    print(f"[{'PASS' if passed else 'FAIL'}] {name}")
    if not passed:
        ok = False
        if help_text:
            print(f"       -> {help_text}")


step(f"Python {sys.version.split()[0]} (need 3.10+)", sys.version_info >= (3, 10),
     "Install Python 3.11 (see README, Part 2)")

try:
    import boto3
    import strands  # noqa: F401
    step("Libraries installed (boto3, strands-agents)", True)
except ImportError as e:
    step("Libraries installed (boto3, strands-agents)", False, f"Run: pip install -r requirements.txt ({e})")
    sys.exit(1)

try:
    ident = boto3.client("sts", region_name=REGION).get_caller_identity()
    step(f"AWS login works (account {ident['Account']})", True)
except Exception as e:
    step("AWS login works", False, f"Open CloudShell from the AWS Console ({type(e).__name__})")

try:
    br = boto3.client("bedrock-runtime", region_name=REGION)
    r = br.converse(modelId=MODEL_ID, messages=[{"role": "user", "content": [{"text": "Say hello in 3 words"}]}],
                    inferenceConfig={"maxTokens": 20})
    reply = r["output"]["message"]["content"][0]["text"].strip()
    step(f"Bedrock model {MODEL_ID} replied: {reply!r}", True)
except Exception as e:
    if "per day" in str(e):
        hint = (f"Your account's daily Bedrock token quota in {REGION} is used up. Try us-east-1, or "
                "Service Quotas -> Amazon Bedrock -> search 'Nova Pro' -> Request increase")
    else:
        hint = f"Check region is {REGION} and the model works in the Bedrock Playground"
    step(f"Bedrock model {MODEL_ID}", False, f"{hint} ({type(e).__name__}: {e})")

print("\nAll good. You're ready for the workshop!" if ok else "\nFix the FAIL items above, then run this again.")
