#!/usr/bin/env bash
set -eo pipefail

INSTALL_DIR="$HOME/.local/bin"
TMP_DIR=$(mktemp -d)

# Ensure temporary directory is always cleaned up on exit
trap 'rm -rf "$TMP_DIR"' EXIT

log() {
    echo -e "\n\033[1;34m==>\033[0m \033[1m$1\033[0m"
}

get_latest_release() {
    local repo=$1
    curl -sL "https://api.github.com/repos/$repo/releases/latest" | grep -Po '"tag_name": "\K[^"]*' || echo "latest"
}

is_installed() {
    command -v "$1" >/dev/null 2>&1
}

setup_path() {
    log "Setting up $INSTALL_DIR..."
    mkdir -p "$INSTALL_DIR"
    
    if ! grep -q 'export PATH="$HOME/.local/bin:$PATH"' ~/.bashrc; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
        log "Added $INSTALL_DIR to PATH in ~/.bashrc"
    fi
    export PATH="$INSTALL_DIR:$PATH"
}

install_neovim() {
    local latest
    latest=$(get_latest_release "neovim/neovim")
    
    if is_installed nvim; then
        local current
        current=$(nvim --version | head -n 1 | awk '{print $2}')
        if [[ "$current" == "$latest" ]]; then
            log "Neovim is up-to-date ($current). Skipping..."
            return
        fi
        log "Updating Neovim from $current to $latest..."
    else
        log "Installing Neovim ($latest)..."
    fi

    cd "$TMP_DIR"
    local url="https://github.com/neovim/neovim/releases/download/${latest}/nvim-linux-x86_64.tar.gz"
    if [[ "$latest" == "latest" ]]; then
        url="https://github.com/neovim/neovim/releases/latest/download/nvim-linux-x86_64.tar.gz"
    fi
    curl -LO "$url"
    tar -xzf nvim-linux-x86_64.tar.gz
    cp -r nvim-linux-x86_64/* "$HOME/.local/"
}

install_lazygit() {
    local latest
    latest=$(get_latest_release "jesseduffield/lazygit")
    local version_stripped="${latest#v}"
    
    if is_installed lazygit; then
        local current
        # Parse version from lazygit output
        current=$(lazygit --version | grep -Po 'version=\K[^,]*' || lazygit --version | awk '{print $6}' | tr -d ',')
        if [[ "$current" == "$version_stripped" ]] || [[ "$current" == "$latest" ]]; then
            log "Lazygit is up-to-date ($latest). Skipping..."
            return
        fi
        log "Updating Lazygit to $latest..."
    else
        log "Installing Lazygit ($latest)..."
    fi

    cd "$TMP_DIR"
    local url="https://github.com/jesseduffield/lazygit/releases/download/${latest}/lazygit_${version_stripped}_Linux_x86_64.tar.gz"
    if [[ "$latest" == "latest" ]]; then
        url="https://github.com/jesseduffield/lazygit/releases/latest/download/lazygit_${version_stripped}_Linux_x86_64.tar.gz"
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
        current=$(agy --version 2>/dev/null | grep -Po 'v\d+\.\d+\.\d+' || echo "unknown")
        if [[ "$current" == "$latest" ]]; then
            log "Antigravity (agy) is up-to-date ($latest). Skipping..."
            return
        fi
        log "Updating Antigravity to $latest..."
    else
        log "Installing Antigravity ($latest)..."
    fi

    cd "$TMP_DIR"
    local url="https://github.com/google-antigravity/antigravity-cli/releases/download/${latest}/agy_cli_linux_x64.tar.gz"
    if [[ "$latest" == "latest" ]]; then
        url="https://github.com/google-antigravity/antigravity-cli/releases/latest/download/agy_cli_linux_x64.tar.gz"
    fi
    curl -LO "$url"
    tar -xzf agy_cli_linux_x64.tar.gz
    mv antigravity "$INSTALL_DIR/agy"
}

install_leaf() {
    local latest
    latest=$(get_latest_release "RivoLink/leaf")
    
    if is_installed leaf; then
        local current
        current=$(leaf --version 2>/dev/null | awk '{print $2}' || echo "unknown")
        local latest_stripped="${latest#v}"
        if [[ "$current" == "$latest_stripped" ]] || [[ "$current" == "$latest" ]]; then
            log "Leaf is up-to-date ($latest). Skipping..."
            return
        fi
        log "Updating Leaf to $latest..."
    else
        log "Installing Leaf ($latest)..."
    fi

    # Leaf's install script handles download directly
    curl -fsSL https://raw.githubusercontent.com/RivoLink/leaf/main/scripts/install.sh | sh -s -- "$INSTALL_DIR"
}

main() {
    setup_path
    install_neovim
    install_lazygit
    install_agy
    install_leaf
    
    log "Installation complete! 🎉"
    log "Run 'source ~/.bashrc' or open a new terminal to start using the tools."
}

main
