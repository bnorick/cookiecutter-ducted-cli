import re
import sys

PACKAGE_PATTERN = r"^[_a-zA-Z][_a-zA-Z0-9]*$"


def validate_package_name(name: str):
    """
    Validate a pyproject.toml project name according to PEP 508.
    
    Rules:
    - Must consist of ASCII letters, digits, underscores, hyphens, and periods
    - Must not start or end with an underscore, hyphen, or period
    
    Args:
        name: The project name to validate
        
    Returns:
        A tuple of (is_valid, error_message)
        If valid, returns (True, None)
        If invalid, returns (False, error_message)
    """
    if not name:
        return False, "Project name cannot be empty"
    
    # Check if name starts or ends with invalid characters
    if name[0] in ('_', '-', '.'):
        return False, f"Project name cannot start with '{name[0]}'"
    
    if name[-1] in ('_', '-', '.'):
        return False, f"Project name cannot end with '{name[-1]}'"
    
    # Check if all characters are valid (ASCII letters, digits, _, -, .)
    if not re.match(r'^[a-zA-Z0-9._-]+$', name):
        return False, "Project name must only contain ASCII letters, digits, underscores, hyphens, and periods"
    
    return True, None


if __name__ == "__main__":
    package_name = "{{ cookiecutter.package_name }}"
    valid, error = validate_package_name(package_name)
    if not valid:
        print(f"ERROR: The package name ({package_name}) is not a valid. {error}.")

        # exit to cancel recipe
        sys.exit(1)

    package = "{{ cookiecutter.package }}"
    if not re.match(PACKAGE_PATTERN, package):
        print(f"ERROR: '{package}' is not a valid Python package name. "
            f"Package names should start with a letter or underscore and be composed entirely "
            f"of letters, digits, and/or underscores.")

        # exit to cancel recipe
        sys.exit(1)
