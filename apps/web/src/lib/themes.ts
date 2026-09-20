/** oshi-app のテーマ ID。表示はブラウザ内だけ。サーバーには送らない。 */

export const DEFAULT_THEME_ID = "default";

export const THEME_OPTIONS = [
  { id: "default", scheme: "light", swatch: "#b8e05c", ja: "緑", en: "Green" },
  { id: "lime-right", scheme: "light", swatch: "#a3e635", ja: "ライム", en: "Lime" },
  { id: "lime-dark", scheme: "dark", swatch: "#84cc16", ja: "ライム暗", en: "Lime dark" },
  { id: "emerald-dark", scheme: "dark", swatch: "#34d399", ja: "エメラルド", en: "Emerald" },
  { id: "sky-dark", scheme: "dark", swatch: "#38bdf8", ja: "空", en: "Sky" },
  { id: "blue-dark", scheme: "dark", swatch: "#3b82f6", ja: "青", en: "Blue" },
  { id: "pink-dark", scheme: "dark", swatch: "#f472b6", ja: "桃", en: "Pink" },
  { id: "purple-dark", scheme: "dark", swatch: "#a78bfa", ja: "紫", en: "Purple" },
  { id: "orange-dark", scheme: "dark", swatch: "#fb923c", ja: "橙", en: "Orange" },
  { id: "red-dark", scheme: "dark", swatch: "#f87171", ja: "赤", en: "Red" },
  { id: "yellow-dark", scheme: "dark", swatch: "#facc15", ja: "黄", en: "Yellow" },
] as const;

export type ThemeId = (typeof THEME_OPTIONS)[number]["id"];

const ALLOWED = new Set<string>(THEME_OPTIONS.map((item) => item.id));

export function sanitizeTheme(raw: string | null): ThemeId {
  if (raw && ALLOWED.has(raw)) {
    return raw as ThemeId;
  }
  return DEFAULT_THEME_ID;
}
