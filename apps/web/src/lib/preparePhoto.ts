const PASS_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);
const ANALYSIS_LIMIT = 10 * 1024 * 1024;
const START_EDGE = 4096;

/** 画面で読める写真は、送る前に JPEG へ縮める。読めなければ元のファイルを返す。 */
export async function preparePhotoFile(file: File): Promise<File> {
  if (PASS_TYPES.has(file.type) && file.size <= ANALYSIS_LIMIT) {
    return file;
  }
  let bitmap: ImageBitmap;
  try {
    bitmap = await createImageBitmap(file);
  } catch {
    return file;
  }
  try {
    const blob = await jpegWithin(bitmap);
    if (!blob) {
      return file;
    }
    const stem = file.name.replace(/\.[^.]+$/, "") || "photo";
    return new File([blob], `${stem}.jpg`, { type: "image/jpeg" });
  } finally {
    bitmap.close();
  }
}

async function jpegWithin(bitmap: ImageBitmap): Promise<Blob | null> {
  let width = bitmap.width;
  let height = bitmap.height;
  const longest = Math.max(width, height);
  if (longest > START_EDGE) {
    const scale = START_EDGE / longest;
    width = Math.max(1, Math.round(width * scale));
    height = Math.max(1, Math.round(height * scale));
  }
  let quality = 0.85;
  let blob = await paint(bitmap, width, height, quality);
  while (blob && blob.size > ANALYSIS_LIMIT) {
    if (quality > 0.5) {
      quality = Math.round((quality - 0.1) * 10) / 10;
    } else if (Math.min(width, height) > 640) {
      width = Math.max(1, Math.round(width * 0.75));
      height = Math.max(1, Math.round(height * 0.75));
      quality = 0.75;
    } else {
      break;
    }
    blob = await paint(bitmap, width, height, quality);
  }
  return blob;
}

function paint(bitmap: ImageBitmap, width: number, height: number, quality: number): Promise<Blob | null> {
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    return Promise.resolve(null);
  }
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, width, height);
  ctx.drawImage(bitmap, 0, 0, width, height);
  return new Promise((resolve) => canvas.toBlob((blob) => resolve(blob), "image/jpeg", quality));
}
