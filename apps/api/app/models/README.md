# Vision models

Docker ビルド時に次を取得する。

- `pose_landmarker_full.task`（無ければ lite でも姿勢は動く）
- `selfie_segmenter.tflite`（人の輪郭）

ローカル:

```powershell
.\apps\api\scripts\download_pose_model.ps1
```

モデルが無いときは、その段だけ空で解析は続く。
