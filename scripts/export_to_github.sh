#!/usr/bin/env bash
# export_to_github.sh — init, commit, and push to a PRIVATE GitHub repo.
# Blocks if .env / tfvars / tfstate / .db files are staged.
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -d .git ]; then
  git init
  git config core.longpaths true
fi

git add .

# Guard: never commit secrets/state.
if git diff --cached --name-only | grep -E "(^|/)(\.env|.*\.tfvars$|.*\.tfstate.*|.*\.db)$" | grep -v "terraform.tfvars.example" >/dev/null 2>&1; then
  echo "REFUSING TO COMMIT: secret/state files are staged:"
  git diff --cached --name-only | grep -E "(^|/)(\.env|.*\.tfvars$|.*\.tfstate.*|.*\.db)$"
  exit 1
fi

git commit -m "feat: initialize Project Prometheus Agentic AI Governance Control Plane" || echo "Nothing new to commit."

if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  if gh repo view project-prometheus >/dev/null 2>&1; then
    echo "Repo already exists — pushing:"
    git push -u origin main || git push -u origin master
  else
    gh repo create project-prometheus --private --source=. --push
  fi
  echo "Done: https://github.com/$(gh api user --jq .login)/project-prometheus"
else
  echo "GitHub CLI unavailable or not authenticated. Run manually:"
  echo "  git remote add origin git@github.com:YOUR_USER/project-prometheus.git"
  echo "  git push -u origin main"
  echo "  # or with gh after 'gh auth login':"
  echo "  gh repo create project-prometheus --private --source=. --push"
fi
