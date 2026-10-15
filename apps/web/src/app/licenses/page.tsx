"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import notices from "@/data/generated/third_party_notices.json";
import { hydrateAccountPrefs, LOCALE_KEY } from "@/lib/accountPrefs";
import { currentSession } from "@/lib/api";
import { sanitizeLocale, text, type Locale } from "@/lib/messages";

type NoticePackage = {
  name: string;
  version: string;
  license: string;
  ecosystem: string;
  homepage?: string;
};

type NoticeService = {
  id: string;
  name_ja: string;
  attribution_required: boolean;
  status: string;
  note_ja: string;
  docs_url: string | null;
};

export default function LicensesPage() {
  const [locale, setLocale] = useState<Locale>("ja");

  useEffect(() => {
    const stored = sanitizeLocale(window.localStorage.getItem(LOCALE_KEY));
    setLocale(stored);
    document.documentElement.lang = stored;
    void (async () => {
      const current = await currentSession();
      if (!current) {
        return;
      }
      try {
        const prefs = await hydrateAccountPrefs();
        setLocale(prefs.locale);
      } catch (prefError) {
        console.error("preference load failed", prefError);
      }
    })();
  }, []);

  const packages = notices.packages as NoticePackage[];
  const services = notices.services as NoticeService[];

  return (
    <main className="app notice-page">
      <header className="top">
        <div>
          <h1>{text(locale, "licenses")}</h1>
          <p className="lead">{text(locale, "licensesLead")}</p>
          <p className="hint">
            {text(locale, "licensesGenerated")}: {notices.generated_at}
          </p>
        </div>
        <div className="prefs">
          <Link className="lookup" href="/">
            {text(locale, "licensesBack")}
          </Link>
        </div>
      </header>

      <section>
        <h2>{text(locale, "licensesApp")}</h2>
        <p>{notices.app_notice_ja}</p>
      </section>

      <section>
        <h2>{text(locale, "licensesOss")}</h2>
        <p className="hint">{text(locale, "licensesOssHint")}</p>
        <div className="notice-table-wrap">
          <table className="notice-table">
            <thead>
              <tr>
                <th>{text(locale, "licensesName")}</th>
                <th>{text(locale, "licensesVersion")}</th>
                <th>{text(locale, "licensesLicense")}</th>
                <th>{text(locale, "licensesEcosystem")}</th>
              </tr>
            </thead>
            <tbody>
              {packages.map((item) => (
                <tr key={`${item.ecosystem}:${item.name}`}>
                  <td>
                    {item.homepage ? (
                      <a href={item.homepage} rel="noopener noreferrer" target="_blank">
                        {item.name}
                      </a>
                    ) : (
                      item.name
                    )}
                  </td>
                  <td>{item.version || "—"}</td>
                  <td>{item.license}</td>
                  <td>{item.ecosystem}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2>{text(locale, "licensesServices")}</h2>
        {services.map((service) => (
          <article key={service.id} className="notice-card">
            <h3>{service.name_ja}</h3>
            <p className="hint">
              {text(locale, "licensesStatus")}: {service.status}
              {" · "}
              {service.attribution_required
                ? text(locale, "licensesAttribution")
                : text(locale, "licensesNoAttribution")}
            </p>
            <p>{service.note_ja}</p>
            {service.docs_url ? (
              <p>
                <a href={service.docs_url} rel="noopener noreferrer" target="_blank">
                  {service.docs_url}
                </a>
              </p>
            ) : null}
          </article>
        ))}
      </section>
    </main>
  );
}
