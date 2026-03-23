#!/bin/bash
REPO_DIR="$(git rev-parse --show-toplevel)"
PYPROJECT="$REPO_DIR/pyproject.toml"
CURRENT=$(grep -m1 '^version' "$PYPROJECT" | sed 's/.*"\(.*\)".*/\1/')
MAJOR=$(echo "$CURRENT" | cut -d. -f1)
MINOR=$(echo "$CURRENT" | cut -d. -f2)
PATCH=$(echo "$CURRENT" | cut -d. -f3)
NEW_VERSION="$MAJOR.$MINOR.$((PATCH + 1))"
sed -i "s/^version = \"$CURRENT\"/version = \"$NEW_VERSION\"/" "$PYPROJECT"
git add "$PYPROJECT"
echo "Version bumped: $CURRENT -> $NEW_VERSION"
