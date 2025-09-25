# We pin the YARF version this way because snapcraft runs pip install
# and does not use uv automatically, so uv add <dep> will not work because
# pip will not look into tool.uv.sources.

set -euo pipefail
f=examples/yarf-example-plugin/pyproject.toml

# remove any bare "yarf"
sed -i '/"yarf"\s*,\?$/d' "$f"

# Get commit sha
COMMIT_SHA=$(PYTHONPATH=$(echo /snap/yarf/current/lib/**/site-packages) python3 -c "from yarf import metadata; print(metadata.COMMIT_SHA)")

# Prepend the pinned YARF dep.
# We use main here because that is the same as what is on edge channel
# since we publish the YARF snap to snapstore on each merge to main.
awk -v sha="$COMMIT_SHA" '
BEGIN{added=0}
{print}
/^\[project\]/{inproj=1}
inproj && /^\s*dependencies\s*=\s*\[/{
    print "    \"yarf @ git+https://github.com/canonical/yarf.git@" sha "\","
    inproj=0; added=1
}
END{if(!added) exit 0}
' "$f" > "$f.tmp" && mv "$f.tmp" "$f"
