#!/bin/bash
# Wrapper script for remote execution via restricted SSH key
# This script sets up the environment then calls regtest.py

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK_DIR="$(dirname "$SCRIPT_DIR")"

# Parse SSH_ORIGINAL_COMMAND if present
if [ -n "$SSH_ORIGINAL_COMMAND" ]; then
    # Extract command and ini file from SSH_ORIGINAL_COMMAND
    # Expected format: "regtest.py <command> <ini_file>" or "/path/to/regtest.py <command> <ini_file>"
    if [[ "$SSH_ORIGINAL_COMMAND" =~ regtest\.py[[:space:]]+([a-z]+)[[:space:]]+([^[:space:]]+) ]]; then
        COMMAND="${BASH_REMATCH[1]}"
        INI_FILE="${BASH_REMATCH[2]}"
    else
        echo "ERROR: Invalid SSH command format: $SSH_ORIGINAL_COMMAND" >&2
        echo "Expected: regtest.py <command> <ini_file>" >&2
        echo "Where <command> is one of: setup, submit, check, extract, www" >&2
        exit 1
    fi
else
    # Direct execution - use command line arguments
    COMMAND="$1"
    INI_FILE="$2"
fi

# Validate command
case "$COMMAND" in
    setup|submit|check|extract|www)
        ;;
    *)
        echo "ERROR: Invalid command: $COMMAND" >&2
        echo "Valid commands: setup, submit, check, extract, www" >&2
        exit 1
        ;;
esac

# Validate INI file (except for www command which doesn't need one)
if [ "$COMMAND" != "www" ]; then
    if [ -z "$INI_FILE" ]; then
        echo "ERROR: INI file required for $COMMAND command" >&2
        exit 1
    fi
    
    # Security check: no absolute paths or parent directory references
    if [[ "$INI_FILE" == /* ]] || [[ "$INI_FILE" == *".."* ]]; then
        echo "ERROR: Invalid INI file path: $INI_FILE" >&2
        echo "INI file must be a relative path without '..'" >&2
        exit 1
    fi
fi

# Change to work directory
cd "$WORK_DIR" || exit 1

# Find and source the environment setup script
# Look for env_setup_ucx.sh in the INI file's directory or current directory
if [ -n "$INI_FILE" ]; then
    INI_DIR="$(dirname "$INI_FILE")"
    if [ -f "$INI_DIR/env_setup_ucx.sh" ]; then
        ENV_SCRIPT="$INI_DIR/env_setup_ucx.sh"
    elif [ -f "env_setup_ucx.sh" ]; then
        ENV_SCRIPT="env_setup_ucx.sh"
    else
        # Try to find it in one of the standard locations
        for dir in A B C reference .; do
            if [ -f "$dir/env_setup_ucx.sh" ]; then
                ENV_SCRIPT="$dir/env_setup_ucx.sh"
                break
            fi
        done
    fi
else
    # For www command, just look in standard locations
    for dir in A . ; do
        if [ -f "$dir/env_setup_ucx.sh" ]; then
            ENV_SCRIPT="$dir/env_setup_ucx.sh"
            break
        fi
    done
fi

# Source the environment if found
if [ -n "$ENV_SCRIPT" ] && [ -f "$ENV_SCRIPT" ]; then
    echo "==> Loading environment from: $ENV_SCRIPT"
    source "$ENV_SCRIPT"
else
    echo "WARNING: No env_setup_ucx.sh found, using current environment"
fi

# Verify Python is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found in PATH" >&2
    exit 1
fi

# Execute regtest.py with the command and arguments
echo "==> Executing: python3 $SCRIPT_DIR/regtest.py $COMMAND $INI_FILE"
exec python3 "$SCRIPT_DIR/regtest.py" "$COMMAND" "$INI_FILE"