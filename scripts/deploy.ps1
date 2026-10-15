# ローカルの gcloud で Cloud Run に出す。
# 使い方（リポジトリ直下）: powershell -File scripts/deploy.ps1
# 秘密は読まない。SESSION_SIGNING_SECRET は Cloud Run に既にある値を残す。
$ErrorActionPreference = "Stop"
$Project = "illustration-support"
$Region = "asia-northeast2"
$RuntimeSa = "run-runtime@illustration-support.iam.gserviceaccount.com"
$EnvVars = "GOOGLE_CLOUD_PROJECT=illustration-support,GOOGLE_CLOUD_LOCATION=global,GOOGLE_GENAI_USE_ENTERPRISE=True,GCS_BUCKET=illustration-support-photos,SESSION_COOKIE_SECURE=true"

if (-not (Test-Path "apps/api/Dockerfile")) {
  Write-Error "apps/api/Dockerfile がまだありません。"
}

gcloud run deploy illustration-api `
  --source apps/api `
  --region $Region `
  --project $Project `
  --service-account $RuntimeSa `
  --allow-unauthenticated `
  --max-instances 2 `
  --update-env-vars $EnvVars

$apiUrl = gcloud run services describe illustration-api --region $Region --project $Project --format="value(status.url)"
Write-Output "API: $apiUrl"

if (-not (Test-Path "apps/web/Dockerfile")) {
  Write-Error "apps/web/Dockerfile がまだありません。"
}

gcloud run deploy illustration-web `
  --source apps/web `
  --region $Region `
  --project $Project `
  --allow-unauthenticated `
  --max-instances 2 `
  --update-env-vars "API_BASE_URL=$apiUrl,NEXT_PUBLIC_API_BASE_URL=/drawref-api"

$webUrl = gcloud run services describe illustration-web --region $Region --project $Project --format="value(status.url)"
gcloud run services update illustration-api `
  --region $Region `
  --project $Project `
  --update-env-vars "CORS_ORIGINS=$webUrl"

Write-Output "WEB: $webUrl"
