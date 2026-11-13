#!/usr/bin/env bash
# Stops ingestion, Gemini calls and API traffic within seconds. Data is kept. Re-enable with: ./scripts/emergency-shutdown.sh restore
set -euo pipefail
STACK="${STACK:-news-platform}"; MODE="${1:-stop}"
fn() { aws cloudformation describe-stack-resource --stack-name "$STACK" --logical-resource-id "$1" --query StackResourceDetail.PhysicalResourceId --output text; }
for L in ApiFunction IngestionFunction HeadlineBackfillFunction CleanupFunction; do
  F="$(fn $L)"
  if [ "$MODE" = "stop" ]; then aws lambda put-function-concurrency --function-name "$F" --reserved-concurrent-executions 0 >/dev/null
  else aws lambda delete-function-concurrency --function-name "$F" >/dev/null; fi
  echo "$MODE: $F"
done
[ "$MODE" = "stop" ] && echo "Stopped. Rotate the Gemini key in Google AI Studio if you suspect abuse. For full removal: aws cloudformation delete-stack --stack-name $STACK (empty the S3 bucket first)."
echo "Note: restore resets reserved concurrency to the account default; re-run 'sam deploy' to re-apply the template limits."
