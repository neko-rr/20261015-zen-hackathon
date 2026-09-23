# ローカル開発用: 姿勢（full）と人マスクのモデルを落とす
$ErrorActionPreference = "Stop"
$outDir = Join-Path $PSScriptRoot "..\app\models"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$files = @(
  @{
    Name = "pose_landmarker_full.task"
    Url = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task"
  },
  @{
    Name = "selfie_segmenter.tflite"
    Url = "https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_segmenter/float16/latest/selfie_segmenter.tflite"
  }
)

foreach ($item in $files) {
  $outFile = Join-Path $outDir $item.Name
  Write-Host "Downloading $($item.Name)..."
  curl.exe -L --retry 3 -o $outFile $item.Url
  if (-not (Test-Path $outFile) -or (Get-Item $outFile).Length -lt 100KB) {
    throw "Download failed or file too small: $outFile"
  }
  Write-Host "Saved $outFile ($((Get-Item $outFile).Length) bytes)"
}
