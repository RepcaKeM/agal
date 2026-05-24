# Repo-recon — fast commands

## Inventory
```bash
# Top-level layout
ls -la
# Top dirs by file count
find . -type d -not -path '*/.git/*' -not -path '*/node_modules/*' \
  -exec sh -c 'echo "$(find "$0" -maxdepth 1 -type f | wc -l) $0"' {} \; \
  | sort -rn | head -20

# Largest files (often generated; sometimes the gnarly core)
find . -type f -not -path '*/.git/*' -not -path '*/node_modules/*' \
  -exec du -k {} + | sort -rn | head -20
```

## Entry points
```bash
# Look for usual suspects
grep -rE "^(if __name__|func main|fn main|app\.listen|exports\.handler|@app\.route|@\w+\.route)" \
  --include="*.py" --include="*.go" --include="*.rs" --include="*.ts" --include="*.js" .
```

## Hot files (most-changed)
```bash
git log --pretty=format: --name-only --since="6 months ago" \
  | grep -v '^$' | sort | uniq -c | sort -rg | head -30
```

## Module imports (who depends on whom)
```bash
# Python
rg "^(from|import) " --type py | sed 's/.* //' | sort -u

# TypeScript/JavaScript
rg "from ['\"]" --type ts -N | awk -F"'" '{print $2}' | sort -u
```

## Configuration surface
```bash
# Env vars referenced
rg "process\.env\.|os\.environ|os\.getenv" -l
rg "process\.env\.|os\.environ\.get" --no-heading | grep -oE "[A-Z_][A-Z0-9_]+" | sort -u

# Config files
find . -maxdepth 3 \( -name "*.yml" -o -name "*.yaml" -o -name "*.toml" -o -name "*.json" \) \
  -not -path '*/node_modules/*' | head -30
```

## Test entry points
```bash
# Common test frameworks
find . -path '*/test*' -type f \( -name "*.test.*" -o -name "test_*.py" -o -name "*_test.go" \) \
  -not -path '*/node_modules/*' | head -20
```
