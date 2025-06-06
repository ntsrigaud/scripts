#!/bin/bash

# Default installation directory
INSTALL_DIR="$HOME/.local/bin"

# Ensure the install directory exists
mkdir -p "$INSTALL_DIR"

echo "Installing scripts to $INSTALL_DIR..."

# Iterate over all .sh scripts in the current directory
for script in *.sh; do
  if [ -x "$script" ]; then
    cp "$script" "$INSTALL_DIR"
    echo "Installed: $script → $INSTALL_DIR/$script"
  else
    echo "Skipping $script (not executable)"
  fi
done

# Ensure the install path is in the user's shell PATH
SHELL_RC="$HOME/.zshrc"
if [ -n "$BASH_VERSION" ]; then
  SHELL_RC="$HOME/.bashrc"
fi

# Add export to shell config only if not already present
if ! grep -q "$INSTALL_DIR" "$SHELL_RC"; then
  echo "export PATH=\"$INSTALL_DIR:\$PATH\"" >> "$SHELL_RC"
  echo "Updated $SHELL_RC to include $INSTALL_DIR in PATH"
else
  echo "$INSTALL_DIR already in PATH"
fi

echo "✅ All done. Restart your terminal or run 'source $SHELL_RC' to use the installed scripts."