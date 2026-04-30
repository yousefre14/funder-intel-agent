"""
Path management for local vs cloud deployment.

WHY THIS EXISTS:
Streamlit Cloud has a read-only filesystem except /tmp/.
Locally, we write to data/output/.
This module handles the difference automatically.
"""

import os
import tempfile


def get_output_dir() -> str:
    """Get the writable output directory"""
    
    if os.environ.get("STREAMLIT_CLOUD"):
        # Cloud: use /tmp/
        output_dir = os.path.join(tempfile.gettempdir(), "funder_output")
    else:
        # Local: use data/output/
        output_dir = os.path.join("data", "output")
    
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def get_output_path(filename: str) -> str:
    """Get full path for an output file"""
    return os.path.join(get_output_dir(), filename)


def get_safe_name(funder_name: str) -> str:
    """Convert funder name to safe filename"""
    safe_name = funder_name.lower().replace(" ", "_")
    safe_name = "".join(c for c in safe_name if c.isalnum() or c == "_")
    return safe_name