#!/usr/bin/env bash
# Usage: ./scripts/deploy.sh <alert-email>   (requires aws cli, sam cli, node 20+, python 3.12)
set -euo pipefail
EMAIL="${1:?alert email required}"; STACK="${STACK:-news-platform}"
cd "$(dirname "$0")/.."
sam build -t infrastructure/template.yaml
sam deploy --stack-name "$STACK" --resolve-s3 --capabilities CAPABILITY_IAM \
  --parameter-overrides "AlertEmail=$EMAIL" "AllowedOrigin=${ALLOWED_ORIGIN:-http://localhost:5173}"
out() { aws cloudformation describe-stacks --stack-name "$STACK" --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }
API="$(out ApiUrl)"; BUCKET="$(out SiteBucketName)"; DIST="$(out DistributionId)"
( cd frontend && npm ci && VITE_API_BASE_URL="$API" npm run build )
aws s3 sync frontend/dist "s3://$BUCKET" --delete
aws cloudfront create-invalidation --distribution-id "$DIST" --paths "/*" >/dev/null
echo "Site: $(out SiteUrl)  (now redeploy with ALLOWED_ORIGIN set to this URL so CORS allows it)"
