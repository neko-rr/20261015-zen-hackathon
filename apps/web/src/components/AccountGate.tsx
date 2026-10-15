"use client";

import { useState } from "react";

import {
  ApiError,
  loginAccount,
  logoutAccount,
  registerAccount,
  suggestUsername,
  type SessionInfo,
} from "@/lib/api";
import { text, type Locale } from "@/lib/messages";

type Mode = "login" | "register";

export function AccountGate({
  locale,
  onLocale,
  onSignedIn,
}: {
  locale: Locale;
  onLocale: (locale: Locale) => void;
  onSignedIn: (session: SessionInfo) => void;
}) {
  const [mode, setMode] = useState<Mode>("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [suggesting, setSuggesting] = useState(false);
  const [error, setError] = useState("");

  async function onSuggest() {
    setSuggesting(true);
    setError("");
    try {
      setUsername(await suggestUsername());
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : text(locale, "suggestUsername"));
    } finally {
      setSuggesting(false);
    }
  }

  async function onSubmit() {
    setBusy(true);
    setError("");
    try {
      const session =
        mode === "login"
          ? await loginAccount(username, password)
          : await registerAccount(username, password);
      setPassword("");
      onSignedIn(session);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : text(locale, "sessionNeeded"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="gate-wrap">
      <form
        className="gate"
        onSubmit={(event) => {
          event.preventDefault();
          void onSubmit();
        }}
      >
        <h1>{text(locale, "title")}</h1>
        <p className="lead">{text(locale, "gateLead")}</p>
        <div className="locale">
          <button
            type="button"
            aria-pressed={mode === "login"}
            onClick={() => {
              setMode("login");
              setError("");
            }}
          >
            {text(locale, "haveAccount")}
          </button>
          <button
            type="button"
            aria-pressed={mode === "register"}
            onClick={() => {
              setMode("register");
              setError("");
            }}
          >
            {text(locale, "needAccount")}
          </button>
        </div>
        <label htmlFor="account-name">{text(locale, "username")}</label>
        <input
          id="account-name"
          value={username}
          autoComplete="username"
          onChange={(event) => setUsername(event.target.value)}
        />
        {mode === "register" ? (
          <div className="locale">
            <button type="button" disabled={busy || suggesting} onClick={() => void onSuggest()}>
              {text(locale, "suggestUsername")}
            </button>
          </div>
        ) : null}
        <label htmlFor="account-password">{text(locale, "password")}</label>
        <input
          id="account-password"
          type="password"
          value={password}
          autoComplete={mode === "login" ? "current-password" : "new-password"}
          onChange={(event) => setPassword(event.target.value)}
        />
        {mode === "register" ? (
          <p className="hint">
            {text(locale, "usernameRule")} {text(locale, "passwordRule")}
          </p>
        ) : null}
        <p className="hint">{text(locale, "identityHint")}</p>
        <p className="hint">{text(locale, "reviewerHint")}</p>
        {error ? <p className="error">{error}</p> : null}
        <button className="gate-submit" type="submit" disabled={busy || !username.trim() || !password}>
          {busy ? text(locale, "loggingIn") : text(locale, mode === "login" ? "login" : "register")}
        </button>
        <div className="locale">
          <button type="button" aria-pressed={locale === "ja"} onClick={() => onLocale("ja")}>
            日本語
          </button>
          <button type="button" aria-pressed={locale === "en"} onClick={() => onLocale("en")}>
            English
          </button>
        </div>
      </form>
    </main>
  );
}

export function SignedIn({
  locale,
  username,
  onLoggedOut,
}: {
  locale: Locale;
  username: string;
  onLoggedOut: () => void;
}) {
  const [busy, setBusy] = useState(false);

  async function onLogout() {
    setBusy(true);
    try {
      await logoutAccount();
    } catch (caught) {
      console.error("logout failed", caught);
    } finally {
      setBusy(false);
      onLoggedOut();
    }
  }

  return (
    <div className="who">
      <span className="hint">{text(locale, "accountReady")}</span>
      <strong>{username || text(locale, "accountReady")}</strong>
      <button type="button" disabled={busy} onClick={() => void onLogout()}>
        {text(locale, "logout")}
      </button>
    </div>
  );
}
