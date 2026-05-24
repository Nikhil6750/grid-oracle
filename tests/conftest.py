"""
conftest.py — ensures pytest working directory is project root
so relative paths in prediction_service.py resolve correctly.
"""
import os
import pytest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent  # pitwall-ai-backend/

@pytest.fixture(autouse=True, scope="session")
def set_project_root_cwd():
    original = os.getcwd()
    os.chdir(ROOT_DIR)
    yield
    os.chdir(original)
