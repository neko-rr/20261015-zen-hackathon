# ローカルの gcloud で Cloud Run に出す。
# 使い方（リポジトリ直下）: powershell -File scripts/deploy.ps1
$ErrorActionPreference = "Stop"
$Project = "illustration-support"
$Region = "asia-northeast2"
$RuntimeSa = "run-runtime@illustration-support.iam.gserviceaccount.com"
$EnvVars = "GOOGLE_CLOUD_PROJECT=illustration-support,GOOGLE_CLOUD_LOCATION=global,GOOGLE_GENAI_USE_ENTERPRISE=True,GCS_BUCKET=illustration-support-photos"

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
  --set-env-vars $EnvVars

$apiUrl = gcloud run services describe illustration-api --region $Region --project $Project --format="value(status.url)"
Write-Output "API: $apiUrl"

if (Test-Path "apps/web/Dockerfile") {
  gcloud run deploy illustration-web `
    --source apps/web `
    --region $Region `
    --project $Project `
    --allow-unauthenticated `
    --max-instances 2 `
    --set-env-vars "NEXT_PUBLIC_API_BASE_URL=$apiUrl"
  $webUrl = gcloud run services describe illustration-web --region $Region --project $Project --format="value(status.url)"
  Write-Output "WEB: $webUrl"
} else {
  Write-Output "apps/web/Dockerfile が無いので画面はまだ載せません。"
}
