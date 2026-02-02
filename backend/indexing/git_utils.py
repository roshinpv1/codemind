import os
import subprocess
import uuid
import re

def clone_repo(repo_url: str, branch: str) -> dict:
    """
    Clones or updates a git repository.
    Returns metadata including local path and a new run_id.
    """
    # Ensure CODEBASE_ROOT exists
    root = os.environ.get("CODEBASE_ROOT", "./data/repos")
    if not os.path.exists(root):
        os.makedirs(root, exist_ok=True)
    
    # Extract repo name
    # https://github.com/org/repo.git -> repo
    # Handle various git url formats roughly
    repo_name = repo_url.split("/")[-1]
    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]
    
    # Sanitize for path
    safe_repo = re.sub(r'[^a-zA-Z0-9_-]', '', repo_name)
    safe_branch = re.sub(r'[^a-zA-Z0-9_-]', '', branch)
    
    # Target directory - requirement says reuse.
    # Requirement 4.2 says /data/repos/{uuid}_{repo}_{branch}/
    # To satisfy "uuid" and "reuse", I'll generate a UUID based on the repo_url (namespace uuid).
    repo_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, repo_url))
    
    dir_name = f"{repo_uuid}_{safe_repo}_{safe_branch}"
    repo_path = os.path.join(root, dir_name)
    
    # Basic Security Check: ensure we are somehow inside root? 
    # (os.path.join handles this mostly, but good to be aware)

    try:
        if os.path.exists(repo_path):
            # Pull / Update
            print(f"Updating repo at {repo_path}")
            subprocess.check_output(["git", "fetch", "origin", branch], cwd=repo_path, stderr=subprocess.STDOUT)
            subprocess.check_output(["git", "reset", "--hard", f"origin/{branch}"], cwd=repo_path, stderr=subprocess.STDOUT)
        else:
            # Clone
            print(f"Cloning {repo_url} to {repo_path}")
            subprocess.check_output(["git", "clone", "--branch", branch, "--depth", "1", repo_url, repo_path], stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        error_msg = e.output.decode() if e.output else str(e)
        raise RuntimeError(f"Git operation failed: {error_msg}")
        
    run_id = str(uuid.uuid4())
    
    return {
        "path": repo_path,
        "repo": repo_name,
        "branch": branch,
        "run_id": run_id, 
        "repo_url": repo_url
    }
