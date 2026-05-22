#!/bin/bash
set -euo pipefail

pip install check-jsonschema
uv lock --check
uv tool run tox
