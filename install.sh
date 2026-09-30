#!/usr/bin/env bash
# gea bootstrap installer — Linux, macOS, and WSL.
#
#   gh api -H "Accept: application/vnd.github.raw" \
#     repos/codegeaec/gea-manager/contents/install.sh | bash
#
# The repository is private: only GitHub accounts with access to it can
# install gea, and everything below goes through the caller's authenticated
# GitHub CLI session (no token is written to disk or into uv's receipt).
# Re-running this script updates gea to the latest main.
#
# Installs gh and uv if missing, installs gea with uv, then runs `gea setup`
# to walk through the rest of the machine setup (mise-managed CLI tools,
# agent CLIs, herdr, rtk, codegraph, shadcn, global instructions, skills).
set -euo pipefail

BOLD="\033[1m"; GREEN="\033[32m"; RED="\033[31m"; RESET="\033[0m"
info() { printf "${BOLD}==>${RESET} %s\n" "$1"; }
ok()   { printf "${GREEN}  \xe2\x9c\x93${RESET} %s\n" "$1"; }
err()  { printf "${RED}  \xe2\x9c\x97${RESET} %s\n" "$1"; }

GEA_SLUG="codegeaec/gea-manager"
GEA_REPO="git+https://github.com/${GEA_SLUG}"

# --- GitHub access (the repo is private) -----------------------------------------
# `| bash` uses stdin for the script, so anything interactive reads /dev/tty.
if ! command -v gh >/dev/null 2>&1; then
  info "Installing the GitHub CLI (gh) — gea is a private repository"
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update && sudo apt-get install -y gh
  elif command -v brew >/dev/null 2>&1; then
    brew install gh
  fi
  if ! command -v gh >/dev/null 2>&1; then
    err "gh is required. Install it from https://cli.github.com, run 'gh auth login', then re-run this script"
    exit 1
  fi
fi

if ! gh auth status >/dev/null 2>&1; then
  info "Logging in to GitHub"
  if [ -r /dev/tty ]; then
    gh auth login </dev/tty
  else
    err "no terminal available for 'gh auth login' — run it yourself, then re-run this script"
    exit 1
  fi
fi

if ! gh api "repos/${GEA_SLUG}" --silent >/dev/null 2>&1; then
  err "your GitHub account cannot see ${GEA_SLUG} — ask the owner for access, then re-run this script"
  exit 1
fi
ok "GitHub access to ${GEA_SLUG}"

# git asks gh for the token for this one command only: nothing is stored in
# ~/.gitconfig, and uv's receipt keeps the plain repository URL.
gea_git_auth() {
  GIT_TERMINAL_PROMPT=0 \
  GIT_CONFIG_COUNT=2 \
  GIT_CONFIG_KEY_0="credential.https://github.com.helper" GIT_CONFIG_VALUE_0="" \
  GIT_CONFIG_KEY_1="credential.https://github.com.helper" GIT_CONFIG_VALUE_1='!gh auth git-credential' \
  "$@"
}

if command -v uv >/dev/null 2>&1; then
  ok "uv already installed"
else
  info "Installing uv"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # shellcheck disable=SC1091
  source "$HOME/.local/bin/env" 2>/dev/null || export PATH="$HOME/.local/bin:$PATH"
  if ! command -v uv >/dev/null 2>&1; then
    err "could not install uv — install it manually from https://astral.sh/uv and re-run this script"
    exit 1
  fi
  ok "uv installed"
fi

info "Installing gea"
gea_git_auth uv tool install --force "$GEA_REPO"

if ! command -v gea >/dev/null 2>&1; then
  export PATH="$HOME/.local/bin:$PATH"
fi

if ! command -v gea >/dev/null 2>&1; then
  err "gea installed but not on PATH yet — open a new terminal and run: gea setup"
  exit 0
fi

ok "gea installed"
info "Running gea setup"
gea setup

echo
info "Done. Open a new terminal (or re-source your shell rc) and run: gea"
