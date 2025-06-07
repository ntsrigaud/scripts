#!/usr/bin/env bash

# Detect OS and set default install directory
case "$(uname -s)" in
  Linux)
    INSTALL_DIR="$HOME/.local/bin"
    ;;
  Darwin)
    INSTALL_DIR="/usr/local/bin"
   ;;
  *)
   echo "⚠️ Unsupported OS: $(uname -s). Please manually set the install directory."
   exit 1
   ;;
esac

# Create the directory if it doesn't exist
mkdir -p "$INSTALL_DIR"

echo "📁 Installing scripts to $INSTALL_DIR..."

# Iterate over all .sh scripts in the current directory
for script in *.sh; do
  # Skip the installer script itself
  if [ "$script" == "install_scripts.sh" ]; then
    continue
  fi
  if [ -x "$script" ]; then
    cp -p "$script" "$INSTALL_DIR"
    echo "✅ Installed: $script → $INSTALL_DIR/$script"
  else
    read -p "⚠️  '$script' is not executable. Make it executable and install it? [y/N]: " confirm
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
      chmod +x "$script"
      cp -p "$script" "$INSTALL_DIR"
      echo "✅ Installed: $script → $INSTALL_DIR/$script"
    else
      echo "⏭️ Skipped: $script"
    fi
  fi
done

# Detect current shell
CURRENT_SHELL="$(basename "$SHELL")"
echo "🧠 Detected shell: $CURRENT_SHELL"

# Determine correct shell RC file
case "$CURRENT_SHELL" in
  bash)
    SHELL_RC="$HOME/.bashrc"
    ;;
  zsh)
    SHELL_RC="$HOME/.zshrc"
    ;;
  fish)
    SHELL_RC="$HOME/.config/fish/config.fish"
    ;;
  *)
    echo "⚠️  Unsupported shell: $CURRENT_SHELL. Please manually add $INSTALL_DIR to your PATH."
    exit 1
    ;;
esac

# Check if path is already in RC file
if ! grep -q "$INSTALL_DIR" "$SHELL_RC" 2>/dev/null; then
  echo "" >> "$SHELL_RC"
  if [[ "$CURRENT_SHELL" == "fish" ]]; then
    echo "set -gx PATH \"$INSTALL_DIR\" \$PATH" >> "$SHELL_RC"
  else
    echo "export PATH=\"$INSTALL_DIR:\$PATH\"" >> "$SHELL_RC"
  fi
  echo "✅ Updated $SHELL_RC to include $INSTALL_DIR in PATH"
else
  echo "📦 $INSTALL_DIR already in PATH in $SHELL_RC"
fi

echo -e "\n🎉 All done!"
echo "🔄 Please restart your terminal or run: source $SHELL_RC"
