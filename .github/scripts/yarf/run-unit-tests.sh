#!/bin/bash
set -euo pipefail

uv lock --check
uv tool run tox
