#!/usr/bin/bash
cd ../output
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    echo "this directory not versionn control"
    exit 1
fi

cd ../input
DEPLOY_FILE=".deploy_counnter"
if [ ! -f "$DEPLOY_FILE" ]; then
    echo 0 > "$DEPLOY_FILE"
fi

DEPLOY_NUM=$(cat "$DEPLOY_FILE")
DEPLOY_NUM=$((DEPLOY_NUM + 1))
echo "$DEPLOY_NUM" > "$DEPLOY_FILE"
cd ../output
git add .
git commit -m "Deploy website $DEPLOY_NUM"

git push

echo "Deploy Number $DEPLOY_NUM sucessfuly."
