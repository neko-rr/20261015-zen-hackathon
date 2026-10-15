"use client";

import { useEffect, useState } from "react";

import { ApiError, citeMaterial, citationRefreshDays, noteProjectLibrary, readMaterial, saveCitationRefreshDays, type Lookup, type Material } from "@/lib/api";
import { text, type Locale } from "@/lib/messages";

type Props = {
  locale: Locale;
  materials: Material[];
  openIds: string[];
  projectId: string;
  onOpenIds: (next: string[]) => void;
  onRecorded: () => void;
  disabled: boolean;
};

export function MaterialDesk({
  locale,
  materials,
  openIds,
  projectId,
  onOpenIds,
  onRecorded,
  disabled,
}: Props) {
  const [pick, setPick] = useState("");
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});
  const [texts, setTexts] = useState<Record<string, string>>({});
  const [cites, setCites] = useState<Record<string, Lookup>>({});
  const [queries, setQueries] = useState<Record<string, string>>({});
  const [dragId, setDragId] = useState("");
  const [notice, setNotice] = useState("");
  const [refreshDays, setRefreshDays] = useState("30");

  useEffect(() => {
    void citationRefreshDays()
      .then((days) => setRefreshDays(String(days)))
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    for (const id of openIds) {
      if (texts[id] !== undefined) {
        continue;
      }
      void readMaterial(id)
        .then((item) => {
          setTexts((prev) => ({ ...prev, [id]: item.text || "" }));
          const saved = item.citation;
          if (!saved?.searched_at) {
            return;
          }
          setCites((prev) => {
            if (prev[id]) {
              return prev;
            }
            return {
              ...prev,
              [id]: {
                object_id: "",
                summary: saved.summary,
                sources: saved.sources,
                search_suggestions_html: "",
                cached: true,
                search_skipped: false,
                searched_at: saved.searched_at,
              },
            };
          });
        })
        .catch(() => {
          setTexts((prev) => ({ ...prev, [id]: "" }));
        });
    }
  }, [openIds, texts]);

  function openPicked() {
    if (!pick || openIds.includes(pick)) {
      return;
    }
    onOpenIds([...openIds, pick]);
    if (!projectId) {
      return;
    }
    void noteProjectLibrary(projectId, pick)
      .then(() => onRecorded())
      .catch((caught) => {
        const message = caught instanceof ApiError ? caught.message : text(locale, "citeFailed");
        setNotice(message);
      });
  }

  function closeCard(id: string) {
    onOpenIds(openIds.filter((item) => item !== id));
  }

  function dropOn(targetId: string) {
    if (!dragId || dragId === targetId) {
      setDragId("");
      return;
    }
    const next = openIds.filter((item) => item !== dragId);
    const index = next.indexOf(targetId);
    next.splice(index < 0 ? next.length : index, 0, dragId);
    onOpenIds(next);
    setDragId("");
  }

  async function onCite(id: string) {
    setNotice("");
    try {
      const result = await citeMaterial(id, queries[id] || "", projectId);
      setCites((prev) => ({ ...prev, [id]: result }));
      if (projectId) {
        onRecorded();
      }
    } catch (caught) {
      const message = caught instanceof ApiError ? caught.message : text(locale, "citeFailed");
      setNotice(message);
    }
  }

  return (
    <section className="material-desk" aria-label={text(locale, "libraryDesk")}>
      <h2>{text(locale, "libraryDesk")}</h2>
      <p className="hint">{text(locale, "libraryDeskHint")}</p>
      <form
        className="material-open-row"
        onSubmit={(event) => {
          event.preventDefault();
          const days = Number(refreshDays);
          void saveCitationRefreshDays(days)
            .then((saved) => {
              setRefreshDays(String(saved));
              setNotice(text(locale, "citationRefreshSaved"));
            })
            .catch((caught) => {
              const message = caught instanceof ApiError ? caught.message : text(locale, "citeFailed");
              setNotice(message);
            });
        }}
      >
        <label htmlFor="citation-refresh">{text(locale, "citationRefresh")}</label>
        <input
          id="citation-refresh"
          type="number"
          min={1}
          max={365}
          value={refreshDays}
          disabled={disabled}
          onChange={(event) => setRefreshDays(event.target.value)}
        />
        <button type="submit" disabled={disabled}>
          {text(locale, "citationRefreshSave")}
        </button>
      </form>
      <p className="hint">{text(locale, "citationRefreshHint")}</p>
      <div className="material-open-row">
        <label htmlFor="material-pick">{text(locale, "libraryPick")}</label>
        <select
          id="material-pick"
          value={pick}
          disabled={disabled || materials.length === 0}
          onChange={(event) => setPick(event.target.value)}
        >
          <option value="">{text(locale, "libraryPickEmpty")}</option>
          {materials.map((item) => (
            <option key={item.doc_id} value={item.doc_id}>
              {item.title}
            </option>
          ))}
        </select>
        <button type="button" disabled={disabled || !pick} onClick={openPicked}>
          {text(locale, "libraryOpen")}
        </button>
      </div>
      {notice ? <p className="error">{notice}</p> : null}
      <div className="material-board">
        {openIds.map((id) => {
          const item = materials.find((row) => row.doc_id === id);
          const title = item?.title || id;
          const folded = Boolean(collapsed[id]);
          const cite = cites[id];
          return (
            <article
              key={id}
              className={`material-card${folded ? " is-collapsed" : ""}${dragId === id ? " is-dragging" : ""}`}
              onDragOver={(event) => event.preventDefault()}
              onDrop={() => dropOn(id)}
            >
              <header className="material-card-head">
                <span
                  className="material-drag"
                  draggable={!disabled}
                  role="button"
                  tabIndex={0}
                  aria-label={text(locale, "libraryMove")}
                  onDragStart={() => setDragId(id)}
                  onDragEnd={() => setDragId("")}
                >
                  {text(locale, "libraryMove")}
                </span>
                <h3>{title}</h3>
                <button
                  type="button"
                  className="sources-toggle"
                  aria-expanded={!folded}
                  onClick={() => setCollapsed((prev) => ({ ...prev, [id]: !folded }))}
                >
                  {folded ? text(locale, "libraryExpand") : text(locale, "libraryFold")}
                </button>
                <button type="button" onClick={() => closeCard(id)}>
                  {text(locale, "libraryClose")}
                </button>
              </header>
              {folded ? null : (
                <div className="material-card-body">
                  <p className="hint">
                    {item?.material_kind === "own_work"
                      ? text(locale, "kindOwn")
                      : text(locale, "kindThird")}
                  </p>
                  <pre className="material-excerpt">{texts[id] || text(locale, "libraryEmptyText")}</pre>
                  <form
                    className="material-cite"
                    onSubmit={(event) => {
                      event.preventDefault();
                      void onCite(id);
                    }}
                  >
                    <label htmlFor={`cite-${id}`}>{text(locale, "citeQuery")}</label>
                    <input
                      id={`cite-${id}`}
                      value={queries[id] || ""}
                      maxLength={80}
                      placeholder={text(locale, "citeQueryHint")}
                      onChange={(event) =>
                        setQueries((prev) => ({ ...prev, [id]: event.target.value }))
                      }
                    />
                    <button type="submit" disabled={disabled}>
                      {text(locale, "citeMaterial")}
                    </button>
                  </form>
                  {cite ? (
                    <div className="material-cite-result">
                      {cite.searched_at ? (
                        <p className="hint">
                          {text(locale, "citationSearchedAt")}: {cite.searched_at.slice(0, 10)}
                          {cite.cached ? ` · ${text(locale, "citationSaved")}` : ""}
                        </p>
                      ) : null}
                      <p>{cite.summary}</p>
                      {cite.search_skipped ? <p className="hint">{text(locale, "rightsSkipped")}</p> : null}
                      <ul>
                        {cite.sources.map((source) => (
                          <li key={source.url || source.title}>
                            {source.url ? (
                              <a href={source.url} target="_blank" rel="noreferrer">
                                {source.title || source.url}
                              </a>
                            ) : (
                              source.title
                            )}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </div>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
