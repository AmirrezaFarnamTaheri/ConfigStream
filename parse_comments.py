import json, sys

with open("pr_inline_comments.json") as f:
    comments = json.load(f)

with open("pr_reviews_full.json") as f:
    reviews = json.load(f)

with open("pr_issue_comments.json") as f:
    issue_comments = json.load(f)

print(f"=== INLINE REVIEW COMMENTS ({len(comments)}) ===")
for c in comments:
    path = c.get("path", "?")
    line = c.get("line", c.get("original_line", "?"))
    body = c.get("body", "")
    print(f"\n--- {path}:{line} ---\n{body[:2000]}")

print(f"\n=== REVIEW BODIES ({len(reviews)}) ===")
for r in reviews:
    state = r.get("state", "?")
    body = r.get("body", "")
    if body.strip():
        print(f"\n--- STATE: {state} ---\n{body[:3000]}")

print(f"\n=== ISSUE/PR COMMENTS ({len(issue_comments)}) ===")
for c in issue_comments:
    body = c.get("body", "")
    print(f"\n--- COMMENT ---\n{body[:3000]}")
