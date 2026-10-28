# Instructor Notes: Build Your First AI Agent with Amazon Bedrock & Strands Agents

## Before the workshop
- [ ] Push this repo to GitHub (public) and update the `git clone` line in the README.
- [ ] Send `docs/PREREQUISITES.md` to learners 3–4 days before.
- [ ] Do a full dry run on a fresh account (Parts 1–8), including the **email arriving**.
- [ ] Check the CloudShell Python version and that `python3.11` installs.
- [ ] Check that the Lambda Console's newest Python runtime works with `lambda_function.py`.

## Agenda (2 hours)

| Time | Section | README |
|---|---|---|
| 0:00–0:05 | Opening hook | — |
| 0:05–0:15 | What is an AI agent? Golden rule | — |
| 0:15–0:25 | CloudShell setup + `check_setup.py` | Part 2 |
| 0:25–0:40 | Create 3 security + 2 cost mistakes | Part 3 |
| 0:40–0:55 | Write the 2 cost checks (TODOs) | Part 4 |
| 0:55–1:05 | Talk to the agent | Part 5 |
| 1:05–1:35 | Automate: SNS → Lambda → test email → schedule | Part 6 |
| 1:35–1:40 | Fix + verify | Part 7 |
| 1:40–1:50 | **Cleanup** together | Part 8 |
| 1:50–2:00 | Wrap-up + Q&A | — |

## Most likely problems
1. **Bedrock access** → catch it in setup (0:15).
2. **SNS subscription not confirmed** → no email. Remind everyone in 6.1.
3. **Lambda timeout** (default 3 seconds) → step 6.4.
4. **Wrong region** → resources not found.
5. **Throttling** with a big class → retry after 30 seconds.

## If running behind
- Students copy the TODOs from `solution/checks.py`.
- Skip 6.7 (schedule). The **Test button email** is the key moment.
- **Never skip Part 8 (cleanup).**
