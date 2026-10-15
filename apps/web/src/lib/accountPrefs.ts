import { accountPreferences, saveAccountPreferences } from "@/lib/api";
import { sanitizeLocale, type Locale } from "@/lib/messages";
import { sanitizeTheme, type ThemeId } from "@/lib/themes";

export const LOCALE_KEY = "drawref:locale";
export const THEME_KEY = "drawref:themeId";

export function rememberPrefs(locale: Locale, themeId: ThemeId) {
  localStorage.setItem(LOCALE_KEY, locale);
  localStorage.setItem(THEME_KEY, themeId);
  document.documentElement.lang = locale;
  document.documentElement.setAttribute("data-theme", themeId);
}

export async function hydrateAccountPrefs(): Promise<{ locale: Locale; themeId: ThemeId }> {
  const prefs = await accountPreferences();
  const locale = sanitizeLocale(prefs.locale);
  const themeId = sanitizeTheme(prefs.theme_id);
  rememberPrefs(locale, themeId);
  return { locale, themeId };
}

export async function persistLocale(locale: Locale): Promise<void> {
  await saveAccountPreferences({ locale });
  localStorage.setItem(LOCALE_KEY, locale);
  document.documentElement.lang = locale;
}

export async function persistTheme(themeId: ThemeId): Promise<void> {
  await saveAccountPreferences({ theme_id: themeId });
  localStorage.setItem(THEME_KEY, themeId);
  document.documentElement.setAttribute("data-theme", themeId);
}
