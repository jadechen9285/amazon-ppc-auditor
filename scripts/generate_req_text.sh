# 1. Export core dependencies + the 'viz' group, stripping strict hashes
uv export --group viz --no-dev --no-hashes > requirements.txt

# 2. Append the Hatchling package mounting instruction
echo "-e ." >> requirements.txt # in case the file doesnt add it automatically