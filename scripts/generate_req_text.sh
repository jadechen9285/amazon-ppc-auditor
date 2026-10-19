# 1. Export runtime dependencies (no dev tooling), stripping strict hashes
uv export --no-dev --no-hashes > requirements.txt

# 2. Append the Hatchling package mounting instruction
grep -qxF -- "-e ." requirements.txt || echo "-e ." >> requirements.txt
