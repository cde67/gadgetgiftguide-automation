"""
One automation cycle for Gadget Gift Guide: rebuilds the full static site from
guides.py (picks up any new guides added since the last run, refreshes cached
images, rebuilds sitemap/homepage) and pushes to the public GitHub repo so
GitHub Pages serves the update.

This script does NOT invent new guide topics itself - that's a separate,
lower-frequency task (see the content-expansion scheduled task) because good
SEO content needs real editorial judgment (accurate, specific, non-generic
blurbs per item), not mechanically templated filler. This script's job is
purely: build whatever's in guides.py right now, and ship it.

Requires GITHUB_TOKEN (fine-grained PAT scoped to this repo, Contents: Read
and write) and AMAZON_ASSOCIATE_TAG + PEXELS_API_KEY in .env.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_site as bs

GITHUB_REPO = "cde67/gadgetgiftguide-automation"


def load_env():
    env = {}
    path = os.path.join(bs.SCRIPT_DIR, ".env")
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env[k] = v
    return env


def sync_to_github(base):
    env = load_env()
    token = env.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN not set - skipping GitHub sync.")
        return False

    remote = f"https://x-access-token:{token}@github.com/{GITHUB_REPO}.git"

    def run(cmd, **kw):
        return subprocess.run(cmd, cwd=base, capture_output=True, text=True, **kw)

    if not os.path.isdir(os.path.join(base, ".git")):
        run(["git", "init"])
        run(["git", "config", "user.name", "Gadget Gift Guide Automation"])
        run(["git", "config", "user.email", "automation@gadgetgiftguide.local"])
        run(["git", "remote", "add", "origin", remote])
        fetch = run(["git", "fetch", "origin", "main"])
        if fetch.returncode == 0:
            run(["git", "checkout", "-B", "main", "origin/main"])
        else:
            run(["git", "checkout", "-B", "main"])
    else:
        run(["git", "remote", "set-url", "origin", remote])
        run(["git", "fetch", "origin", "main"])
        run(["git", "merge", "origin/main", "--no-edit"])

    run(["git", "add", "docs", "guides.py"])
    commit = run(["git", "commit", "-m", "Automated cycle: rebuild site"])
    if commit.returncode != 0:
        print("Nothing new to commit.")
        return True
    push = run(["git", "push", "origin", "main"])
    if push.returncode != 0:
        print(f"GitHub push failed:\n{push.stderr}")
        return False
    return True


def main():
    base = bs.SCRIPT_DIR
    bs.main()
    print(f"Rebuilt site: {len(bs.g.GUIDES)} guides.")

    if sync_to_github(base):
        print("CYCLE COMPLETE: pushed to GitHub Pages.")
    else:
        print("CYCLE INCOMPLETE: site built locally but push failed - see above.")


if __name__ == "__main__":
    main()
