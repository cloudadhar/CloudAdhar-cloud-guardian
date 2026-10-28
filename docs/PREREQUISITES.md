# Before the Workshop: Prerequisites Checklist

**Workshop:** CloudAdhar Cloud Guardian, build an AI agent that protects your AWS account

Please finish this **before** you arrive (about 15 minutes). If something fails, message the organiser before the workshop day.

## You need
- [ ] A laptop with **Chrome or Firefox**. Nothing else to install!
- [ ] Your **own AWS account** (a new Free Tier account is fine) with a card added. Expected cost: a few cents.
- [ ] Access to your **email on your phone or laptop** during the workshop. You'll receive an alert email!

## Step 1: Sign in the right way
- [ ] Sign in with an **IAM user** (or IAM Identity Center user) that has **AdministratorAccess**. Please **don't use the root user**.
  - No IAM user yet? **IAM** → **Users** → **Create user** → tick *Provide user access to the AWS Management Console* → **Attach policies directly** → **AdministratorAccess** → **Create user**. Sign in with the console sign-in URL shown.

## Step 2: Select the region
- [ ] Top-right corner of the AWS Console → **US East (N. Virginia) us-east-1**

## Step 3: Test Amazon Bedrock (most important!)
- [ ] **Amazon Bedrock** → **Playground** (Chat / Text) → **Select model** → **Amazon** → **Nova Pro**
- [ ] Type `Hello` → **Run**
- [ ] ✅ You got a reply. ❌ If you see an access message, follow the prompt and try again after a few minutes.

## Step 4: Test CloudShell
- [ ] Click the `>_` **CloudShell** icon in the top bar of the Console
- [ ] Type `python3 --version` → Enter → ✅ You see a version number

## Nice to have
- [ ] A free GitHub account
- [ ] Basic Python reading (if / for loops). No expert skills needed!

See you at the workshop! 🚀
