#!/usr/bin/env bash
# gea bootstrap installer — Linux, macOS, and WSL.
#
#   curl -fsSL https://raw.githubusercontent.com/codegeaec/gea-manager/main/install.sh | bash
#
# Installs uv if missing, installs gea with it, then runs `gea setup` to
# walk through the rest of the machine setup (mise-managed CLI tools,
# agent CLIs, herdr, rtk, codegraph, shadcn, global instructions, skills).
set -euo pipefail

BOLD="\033[1m"; GREEN="\033[32m"; RED="\033[31m"; RESET="\033[0m"
info() { printf "${BOLD}==>${RESET} %s\n" "$1"; }
ok()   { printf "${GREEN}  \xe2\x9c\x93${RESET} %s\n" "$1"; }
err()  { printf "${RED}  \xe2\x9c\x97${RESET} %s\n" "$1"; }

GEA_REPO="git+https://github.com/codegeaec/gea-manager"

if command -v uv >/dev/null 2>&1; then
  ok "uv already installed"
else
  info "Installing uv"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # shellcheck disable=SC1090
  source "$HOME/.local/bin/env" 2>/dev/null || export PATH="$HOME/.local/bin:$PATH"
  if ! command -v uv >/dev/null 2>&1; then
    err "could not install uv — install it manually from https://astral.sh/uv and re-run this script"
    exit 1
  fi
  ok "uv installed"
fi

info "Installing gea"
uv tool install --force "$GEA_REPO"

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
