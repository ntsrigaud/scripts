#!/usr/bin/env bash
set -eo pipefail

INSTALL_DIR="$HOME/.local/bin"
TMP_DIR=$(mktemp -d)

# Ensure temporary directory is always cleaned up on exit
trap 'rm -rf "$TMP_DIR"' EXIT

log() {
    echo -e "\n\033[1;34m==>\033[0m \033[1m$1\033[0m"
}

# --- OS & Architecture Detection ---
OS="$(uname -s)"
ARCH="$(uname -m)"

if [ "$ARCH" = "x86_64" ] || [ "$ARCH" = "amd64" ]; then
    STD_ARCH="x86_64"
    AGY_ARCH="x64"
elif [ "$ARCH" = "arm64" ] || [ "$ARCH" = "aarch64" ]; then
    STD_ARCH="arm64"
    AGY_ARCH="arm64"
else
    log "Unsupported architecture: $ARCH"
    exit 1
fi

if [ "$OS" = "Linux" ]; then
    NVIM_OS="linux"
    LAZYGIT_OS="Linux"
    AGY_OS="linux"
elif [ "$OS" = "Darwin" ]; then
    NVIM_OS="macos"
    LAZYGIT_OS="Darwin"
    AGY_OS="mac"
else
    log "Unsupported OS: $OS"
    exit 1
fi
# -----------------------------------

get_latest_release() {
    local repo=$1
    # Use awk instead of grep -P for macOS cross-compatibility, and strip carriage returns.
    # Avoid 'exit' in awk to prevent SIGPIPE in curl when pipefail is enabled.
    curl -sL "https://api.github.com/repos/$repo/releases/latest" | awk -F'"' '/"tag_name":/ {if (!found) {print $4; found=1}}' | tr -d '\r' || echo "latest"
}

is_installed() {
    command -v "$1" >/dev/null 2>&1
}

setup_path() {
    log "Setting up $INSTALL_DIR..."
    mkdir -p "$INSTALL_DIR"
    
    local rc_file="$HOME/.bashrc"
    if [ "$OS" = "Darwin" ]; then
        # Default to zsh on newer macOS or bash_profile
        if [ -n "$ZSH_VERSION" ] || [[ "$SHELL" == *"zsh" ]]; then
            rc_file="$HOME/.zshrc"
        else
            rc_file="$HOME/.bash_profile"
        fi
    fi
    
    touch "$rc_file"
    if ! grep -q 'export PATH="$HOME/.local/bin:$PATH"' "$rc_file"; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$rc_file"
        log "Added $INSTALL_DIR to PATH in $rc_file"
    fi
    export PATH="$INSTALL_DIR:$PATH"
}

install_neovim() {
    local latest
    latest=$(get_latest_release "neovim/neovim")
    
    if is_installed nvim; then
        local current
        current=$(nvim --version 2>/dev/null | head -n 1 | awk '{print $2}' || echo "unknown")
        if [ -z "$current" ]; then current="unknown"; fi
        
        if [[ "$current" == "$latest" ]]; then
            log "Neovim is up-to-date ($current). Skipping..."
            return
        fi
        log "Updating Neovim from $current to $latest..."
    else
        log "Installing Neovim ($latest)..."
    fi

    cd "$TMP_DIR"
    local asset="nvim-${NVIM_OS}-${STD_ARCH}.tar.gz"
    local url="https://github.com/neovim/neovim/releases/download/${latest}/${asset}"
    if [[ "$latest" == "latest" ]]; then
        url="https://github.com/neovim/neovim/releases/latest/download/${asset}"
    fi
    
    curl -LO "$url"
    tar -xzf "$asset"
    cp -r "nvim-${NVIM_OS}-${STD_ARCH}/"* "$HOME/.local/"
}

install_lazygit() {
    local latest
    latest=$(get_latest_release "jesseduffield/lazygit")
    local version_stripped="${latest#v}"
    
    if is_installed lazygit; then
        local current
        # Parse version cleanly using standard awk/sed, ignoring execution errors
        current=$(lazygit --version 2>/dev/null | awk -F'version=' '{print $2}' | cut -d, -f1 || true)
        if [ -z "$current" ]; then
            current=$(lazygit --version 2>/dev/null | awk '{print $6}' | tr -d ',' || echo "unknown")
        fi
        if [ -z "$current" ]; then current="unknown"; fi
        
        if [[ "$current" == "$version_stripped" ]] || [[ "$current" == "$latest" ]]; then
            log "Lazygit is up-to-date ($latest). Skipping..."
            return
        fi
        log "Updating Lazygit to $latest..."
    else
        log "Installing Lazygit ($latest)..."
    fi

    cd "$TMP_DIR"
    local asset="lazygit_${version_stripped}_${LAZYGIT_OS}_${STD_ARCH}.tar.gz"
    local url="https://github.com/jesseduffield/lazygit/releases/download/${latest}/${asset}"
    if [[ "$latest" == "latest" ]]; then
        url="https://github.com/jesseduffield/lazygit/releases/latest/download/${asset}"
    fi
    
    curl -Lo lazygit.tar.gz "$url"
    tar -xzf lazygit.tar.gz lazygit
    mv lazygit "$INSTALL_DIR/"
}

install_agy() {
    local latest
    latest=$(get_latest_release "google-antigravity/antigravity-cli")
    
    if is_installed agy; then
        local current
        # Use basic grep -E which is macOS compatible, handle execution errors
        current=$(agy --version 2>/dev/null | grep -Eo 'v[0-9]+\.[0-9]+\.[0-9]+' || echo "unknown")
        if [ -z "$current" ]; then current="unknown"; fi
        
        if [[ "$current" == "$latest" ]]; then
            log "Antigravity (agy) is up-to-date ($latest). Skipping..."
            return
        fi
        log "Updating Antigravity to $latest..."
    else
        log "Installing Antigravity ($latest)..."
    fi

    cd "$TMP_DIR"
    local asset="agy_cli_${AGY_OS}_${AGY_ARCH}.tar.gz"
    local url="https://github.com/google-antigravity/antigravity-cli/releases/download/${latest}/${asset}"
    if [[ "$latest" == "latest" ]]; then
        url="https://github.com/google-antigravity/antigravity-cli/releases/latest/download/${asset}"
    fi
    
    curl -LO "$url"
    tar -xzf "$asset"
    mv antigravity "$INSTALL_DIR/agy"
}

install_leaf() {
    local latest
    latest=$(get_latest_release "RivoLink/leaf")
    
    if is_installed leaf; then
        local current
        current=$(leaf --version 2>/dev/null | awk '{print $2}' || echo "unknown")
        if [ -z "$current" ]; then current="unknown"; fi
        
        local latest_stripped="${latest#v}"
        if [[ "$current" == "$latest_stripped" ]] || [[ "$current" == "$latest" ]]; then
            log "Leaf is up-to-date ($latest). Skipping..."
            return
        fi
        log "Updating Leaf to $latest..."
    else
        log "Installing Leaf ($latest)..."
    fi

    curl -fsSL https://raw.githubusercontent.com/RivoLink/leaf/main/scripts/install.sh | sh -s -- "$INSTALL_DIR"
}

main() {
    setup_path
    install_neovim
    install_lazygit
    install_agy
    install_leaf
    
    log "Installation complete! 🎉"
    if [ "$OS" = "Darwin" ]; then
        log "Run 'source ~/.zshrc' (or ~/.bash_profile) or open a new terminal."
    else
        log "Run 'source ~/.bashrc' or open a new terminal."
    fi
}

main
