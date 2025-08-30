#!/bin/bash
# Setup script for regression testing with batch job support
# Usage: source regtest.setup.sh config.ini [path_to_folder/]

# Function to print messages with formatting
print_msg() {
    echo "==> $1"
}

print_error() {
    echo "ERROR: $1" >&2
}

print_success() {
    echo "✓ $1"
}

# Check if script is being sourced (required for environment changes to persist)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    print_error "This script must be sourced, not executed directly"
    echo "Usage: source regtest.setup.sh config.ini [path_to_folder/]"
    exit 1
fi

# Parse command line arguments
if [ $# -lt 1 ]; then
    print_error "Missing required arguments"
    echo "Usage: source regtest.setup.sh config.ini [path_to_folder/]"
    return 1
fi

CONFIG_FILE="$1"
WORK_DIR="${2:-.}"  # Default to current directory if not provided

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    print_error "Configuration file not found: $CONFIG_FILE"
    return 1
fi

print_msg "Setting up regression testing environment"
print_msg "Config file: $CONFIG_FILE"
print_msg "Work directory: $WORK_DIR"

# Function to extract value from INI file
get_ini_value() {
    local file="$1"
    local key="$2"
    local section="${3:-main}"
    
    # Use awk to extract value from INI file
    awk -F '=' -v section="[$section]" -v key="$key" '
        $0 == section { in_section = 1; next }
        /^\[/ { in_section = 0 }
        in_section && $1 ~ "^[[:space:]]*" key "[[:space:]]*$" {
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", $2)
            print $2
            exit
        }
    ' "$file"
}

# Step a: Create work directory if it doesn't exist
if [ ! -d "$WORK_DIR" ]; then
    print_msg "Creating work directory: $WORK_DIR"
    mkdir -p "$WORK_DIR"
    if [ $? -eq 0 ]; then
        print_success "Work directory created"
    else
        print_error "Failed to create work directory"
        return 1
    fi
else
    print_msg "Work directory already exists: $WORK_DIR"
fi

# Get setupFromFolder and virtualEnvironment from INI file
SETUP_FOLDER=$(get_ini_value "$CONFIG_FILE" "setupFromFolder")
NEW_VIRTUAL_ENV=$(get_ini_value "$CONFIG_FILE" "virtualEnvironment")

# Step b: Source environment module script if setupFromFolder is provided
if [ -n "$SETUP_FOLDER" ]; then
    print_msg "Setup folder specified: $SETUP_FOLDER"
    
    # Check if setup folder exists
    if [ ! -d "$SETUP_FOLDER" ]; then
        print_error "Setup folder does not exist: $SETUP_FOLDER"
        return 1
    fi
    
    # Find env_*.sh script
    ENV_SCRIPT=$(find "$SETUP_FOLDER" -maxdepth 1 -name "env_*.sh" -type f | head -1)
    
    if [ -z "$ENV_SCRIPT" ]; then
        print_error "No env_*.sh script found in $SETUP_FOLDER"
        return 1
    fi
    
    print_msg "Sourcing environment script: $ENV_SCRIPT"
    source "$ENV_SCRIPT"
    if [ $? -eq 0 ]; then
        print_success "Environment modules loaded"
    else
        print_error "Failed to source environment script"
        return 1
    fi
    
    # Store the script name for later copying
    ENV_SCRIPT_NAME=$(basename "$ENV_SCRIPT")
else
    print_msg "No setupFromFolder specified, skipping environment module setup"
fi

# Step c: Activate virtual environment if specified
if [ -n "$NEW_VIRTUAL_ENV" ]; then
    print_msg "Virtual environment specified: $NEW_VIRTUAL_ENV"
    
    # Check if virtual environment exists
    if [ ! -d "$NEW_VIRTUAL_ENV" ]; then
        print_error "Virtual environment does not exist: $NEW_VIRTUAL_ENV"
        return 1
    fi
    
    # Check for activation script
    if [ ! -f "$NEW_VIRTUAL_ENV/bin/activate" ]; then
        print_error "Virtual environment activation script not found: $NEW_VIRTUAL_ENV/bin/activate"
        return 1
    fi
    
    # Deactivate current virtual environment if active
    if [ -n "$VIRTUAL_ENV" ] && command -v deactivate &> /dev/null; then
        print_msg "Deactivating current virtual environment"
        deactivate
    fi
    
    # Activate the specified virtual environment
    print_msg "Activating virtual environment: $NEW_VIRTUAL_ENV"
    source "$NEW_VIRTUAL_ENV/bin/activate"
    if [ $? -eq 0 ]; then
        print_success "Virtual environment activated"
    else
        print_error "Failed to activate virtual environment"
        return 1
    fi
else
    print_msg "No virtual environment specified, using current Python environment"
fi

# Step d: Copy environment script to work directory if needed
if [ -n "$ENV_SCRIPT" ]; then
    DEST_ENV_SCRIPT="$WORK_DIR/$ENV_SCRIPT_NAME"
    
    if [ ! -f "$DEST_ENV_SCRIPT" ]; then
        print_msg "Copying environment script to work directory"
        cp "$ENV_SCRIPT" "$DEST_ENV_SCRIPT"
        if [ $? -eq 0 ]; then
            print_success "Environment script copied: $ENV_SCRIPT_NAME"
        else
            print_error "Failed to copy environment script"
            return 1
        fi
    else
        print_msg "Environment script already exists in work directory: $ENV_SCRIPT_NAME"
    fi
fi

# Step e: Copy tests_input folder if needed
if [ -n "$SETUP_FOLDER" ]; then
    SOURCE_TESTS="$SETUP_FOLDER/tests_input"
    DEST_TESTS="$WORK_DIR/tests_input"
    
    if [ -d "$SOURCE_TESTS" ] || [ -L "$SOURCE_TESTS" ]; then
        if [ ! -d "$DEST_TESTS" ]; then
            print_msg "Copying tests_input folder to work directory"
            # Use -L to follow symbolic links and copy the actual content
            cp -Lr "$SOURCE_TESTS" "$DEST_TESTS"
            if [ $? -eq 0 ]; then
                print_success "tests_input folder copied (followed symbolic links)"
            else
                print_error "Failed to copy tests_input folder"
                return 1
            fi
        else
            print_msg "tests_input folder already exists in work directory"
        fi
    else
        print_msg "No tests_input folder found in setup folder, skipping"
    fi
fi

# Final check: Verify hpc_performance_testing is available
print_msg "Checking for hpc_performance_testing module..."
python -c "import hpc_performance_testing" 2>/dev/null
if [ $? -eq 0 ]; then
    print_success "hpc_performance_testing module is available"
else
    print_error "hpc_performance_testing module not found"
    echo "       Please ensure the mk2025a package is installed in your Python environment"
    return 1
fi

# Summary
echo ""
print_success "Setup completed successfully!"
echo "  Work directory: $WORK_DIR"
if [ -n "$NEW_VIRTUAL_ENV" ]; then
    echo "  Virtual environment: $NEW_VIRTUAL_ENV (active)"
fi
if [ -n "$SETUP_FOLDER" ]; then
    echo "  Environment modules: Loaded from $ENV_SCRIPT_NAME"
fi
echo ""
echo "You can now run regression tests with:"
echo "  python regtest.py submit $CONFIG_FILE $WORK_DIR"
echo "  python regtest.py check $CONFIG_FILE $WORK_DIR"
echo "  python regtest.py extract $CONFIG_FILE $WORK_DIR"
echo "  python regtest.py www $CONFIG_FILE $WORK_DIR"