"""Collect public repository statistics for the profile card."""

from collections import Counter
import json
import os
from urllib.request import Request, urlopen


REPOSITORIES = """
query($login: String!, $cursor: String) {
  user(login: $login) {
    id
    createdAt
    repositories(first: 100, after: $cursor, privacy: PUBLIC, ownerAffiliations: [OWNER],
                 orderBy: {field: NAME, direction: ASC}) {
      nodes {
        name
        isFork
        stargazerCount
        primaryLanguage { name }
        defaultBranchRef { target { oid } }
      }
      pageInfo { hasNextPage endCursor }
    }
  }
}
"""

COMMITS = """
query($login: String!, $repo: String!, $head: GitObjectID!, $author: ID!, $cursor: String) {
  repository(owner: $login, name: $repo) {
    visibility
    object(oid: $head) {
      ... on Commit {
        history(first: 100, after: $cursor, author: {id: $author}) {
          nodes { additions deletions }
          pageInfo { hasNextPage endCursor }
        }
      }
    }
  }
}
"""


def query(document, **variables):
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise RuntimeError("Set GITHUB_TOKEN to read the public GitHub GraphQL API.")
    request = Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": document, "variables": variables}).encode(),
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "github-profile-card",
        },
    )
    with urlopen(request, timeout=45) as response:
        payload = json.load(response)
    if payload.get("errors"):
        messages = [error["message"] for error in payload["errors"]]
        raise RuntimeError("GitHub query failed: " + " / ".join(messages))
    return payload["data"]


def commit_stats(login, repo, head, author):
    """Sum this author's available history at the captured default-branch tip."""
    count = added = removed = 0
    cursor = None
    while True:
        repository = query(COMMITS, login=login, repo=repo, head=head, author=author, cursor=cursor)["repository"]
        if not repository or repository["visibility"] != "PUBLIC":
            raise RuntimeError(f"Public repository {repo} became unavailable during collection.")
        page = repository["object"]["history"]
        count += len(page["nodes"])
        for commit in page["nodes"]:
            added += commit["additions"]
            removed += commit["deletions"]
        if not page["pageInfo"]["hasNextPage"]:
            return count, added, removed
        cursor = page["pageInfo"]["endCursor"]


def fetch_stats(login):
    """Include forks in the repository count and exclude them from all other metrics."""
    repo_count = stars = commits = added = removed = 0
    languages = Counter()
    cursor = None
    while True:
        user = query(REPOSITORIES, login=login, cursor=cursor)["user"]
        page = user["repositories"]
        for repo in page["nodes"]:
            repo_count += 1
            if repo["isFork"]:
                continue
            stars += repo["stargazerCount"]
            if repo["name"].casefold() == login.casefold():
                continue
            if repo["primaryLanguage"]:
                languages[repo["primaryLanguage"]["name"]] += 1
            if repo["defaultBranchRef"]:
                head = repo["defaultBranchRef"]["target"]["oid"]
                count, additions, deletions = commit_stats(login, repo["name"], head, user["id"])
                commits += count
                added += additions
                removed += deletions
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]
    ranked = sorted(languages, key=lambda name: (-languages[name], name))
    return {
        "repo_count": repo_count,
        "stars": stars,
        "languages": ranked[:3],
        "joined": user["createdAt"][:10],
        "commits": commits,
        "added": added,
        "removed": removed,
    }
