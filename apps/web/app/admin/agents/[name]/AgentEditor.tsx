"use client";

import { useState, useCallback, useRef } from "react";

interface Version {
  id: string;
  saved_by: string | null;
  saved_at: string;
  label: string | null;
}

interface Settings {
  model: string | null;
  temperature: number | null;
  max_tokens: number | null;
}

interface Props {
  agentName: string;
  role: string;
  initialContent: string;
  initialSettings: Settings;
  initialVersions: Version[];
}

// ---------------------------------------------------------------------------
// Simple line-diff for the diff view
// ---------------------------------------------------------------------------
type DiffLine = { type: "same" | "added" | "removed"; text: string };

function lineDiff(original: string, modified: string): DiffLine[] {
  const a = original.split("\n");
  const b = modified.split("\n");
  const result: DiffLine[] = [];
  let i = 0;
  let j = 0;

  while (i < a.length || j < b.length) {
    if (i >= a.length) {
      result.push({ type: "added", text: b[j++] });
    } else if (j >= b.length) {
      result.push({ type: "removed", text: a[i++] });
    } else if (a[i] === b[j]) {
      result.push({ type: "same", text: a[i] });
      i++;
      j++;
    } else {
      // Look ahead up to 8 lines to find next match
      const look = 8;
      let found = false;
      for (let k = 1; k <= look && !found; k++) {
        if (j + k < b.length && a[i] === b[j + k]) {
          for (let l = 0; l < k; l++) result.push({ type: "added", text: b[j + l] });
          j += k;
          found = true;
        } else if (i + k < a.length && a[i + k] === b[j]) {
          for (let l = 0; l < k; l++) result.push({ type: "removed", text: a[i + l] });
          i += k;
          found = true;
        }
      }
      if (!found) {
        result.push({ type: "removed", text: a[i++] });
        result.push({ type: "added", text: b[j++] });
      }
    }
  }
  return result;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function fmtTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const MODEL_SHORT: Record<string, string> = {
  "claude-opus-4-6": "Opus 4.6",
  "claude-sonnet-4-6": "Sonnet 4.6",
  "claude-haiku-4-5-20251001": "Haiku 4.5",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export default function AgentEditor({
  agentName,
  role,
  initialContent,
  initialSettings,
  initialVersions,
}: Props) {
  const [content, setContent] = useState(initialContent);
  const [savedContent, setSavedContent] = useState(initialContent);
  const [settings, setSettings] = useState(initialSettings);
  const [versions, setVersions] = useState(initialVersions);
  const [saving, setSaving] = useState(false);
  const [reverting, setReverting] = useState<string | null>(null);
  const [showConfirm, setShowConfirm] = useState(false);
  const [showDiff, setShowDiff] = useState(false);
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const isDirty = content !== savedContent;

  const lineCount = content.split("\n").length;
  const charCount = content.length;

  const showToast = useCallback((msg: string, ok: boolean) => {
    setToast({ msg, ok });
    setTimeout(() => setToast(null), 3500);
  }, []);

  // Save
  const handleSave = useCallback(async () => {
    setSaving(true);
    setShowConfirm(false);
    try {
      const res = await fetch(`/api/admin/agents/${agentName}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? "Save failed");
      setSavedContent(content);
      if (data.settings) setSettings(data.settings);
      if (data.versions) setVersions(data.versions);
      showToast("Saved successfully", true);
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Save failed", false);
    } finally {
      setSaving(false);
    }
  }, [agentName, content, showToast]);

  // Revert
  const handleRevert = useCallback(
    async (versionId: string) => {
      setReverting(versionId);
      try {
        const res = await fetch(
          `/api/admin/agents/${agentName}?revert=${encodeURIComponent(versionId)}`,
          { method: "POST" }
        );
        const data = await res.json();
        if (!res.ok) throw new Error(data.error ?? "Revert failed");
        setContent(data.content);
        setSavedContent(data.content);
        if (data.versions) setVersions(data.versions);
        setShowDiff(false);
        showToast("Reverted successfully", true);
      } catch (err: unknown) {
        showToast(err instanceof Error ? err.message : "Revert failed", false);
      } finally {
        setReverting(null);
      }
    },
    [agentName, showToast]
  );

  const diff = showDiff ? lineDiff(savedContent, content) : [];

  return (
    <div className="flex flex-col h-[calc(100vh-120px)] min-h-[600px]">
      {/* ── Header ── */}
      <div className="flex items-center justify-between mb-4 flex-shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono font-bold text-[#00e87a] uppercase tracking-widest border border-[#00e87a]/40 px-2 py-1 rounded">
            {agentName}
          </span>
          <span className="text-gray-500 text-sm truncate max-w-sm">{role}</span>
        </div>
        <div className="flex items-center gap-2">
          {isDirty && (
            <span className="text-xs text-amber-400 bg-amber-400/10 border border-amber-400/30 px-2 py-1 rounded">
              Unsaved changes
            </span>
          )}
          <span className="text-xs text-red-400 bg-red-400/10 border border-red-400/30 px-2 py-1 rounded">
            LIVE
          </span>
        </div>
      </div>

      {/* ── Main layout ── */}
      <div className="flex gap-4 flex-1 min-h-0">
        {/* Editor panel */}
        <div className="flex-1 flex flex-col min-w-0">
          {showDiff ? (
            /* Diff view */
            <div className="flex-1 bg-[#0d0d0d] border border-gray-800 rounded-xl overflow-auto font-mono text-xs leading-5">
              <div className="sticky top-0 bg-[#0d0d0d] border-b border-gray-800 px-4 py-2 flex items-center gap-4 text-xs text-gray-500">
                <span className="flex items-center gap-1.5">
                  <span className="inline-block w-2.5 h-2.5 rounded-sm bg-red-500/30 border border-red-500/50" />
                  Removed
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="inline-block w-2.5 h-2.5 rounded-sm bg-[#00e87a]/20 border border-[#00e87a]/40" />
                  Added
                </span>
                <span className="ml-auto text-gray-600">
                  {diff.filter((l) => l.type === "removed").length} removed ·{" "}
                  {diff.filter((l) => l.type === "added").length} added
                </span>
              </div>
              <div className="p-4">
                {diff.map((line, idx) => (
                  <div
                    key={idx}
                    className={`px-2 -mx-2 whitespace-pre-wrap break-all ${
                      line.type === "removed"
                        ? "bg-red-500/10 text-red-300"
                        : line.type === "added"
                        ? "bg-[#00e87a]/10 text-[#00e87a]"
                        : "text-gray-400"
                    }`}
                  >
                    <span className="select-none text-gray-700 mr-3 inline-block w-4 text-right">
                      {line.type === "removed" ? "−" : line.type === "added" ? "+" : " "}
                    </span>
                    {line.text}
                  </div>
                ))}
                {diff.length === 0 && (
                  <p className="text-gray-600 text-center py-8">No changes</p>
                )}
              </div>
            </div>
          ) : (
            /* Text editor */
            <textarea
              ref={textareaRef}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              className="flex-1 w-full bg-[#0d0d0d] border border-gray-800 rounded-xl p-5 font-mono text-xs text-gray-200 leading-5 resize-none focus:outline-none focus:border-gray-700 transition-colors placeholder-gray-700"
              spellCheck={false}
              placeholder="Agent skill content..."
            />
          )}

          {/* Footer bar */}
          <div className="flex items-center justify-between mt-2 flex-shrink-0">
            <div className="flex items-center gap-4 text-xs text-gray-600">
              <span>{lineCount.toLocaleString()} lines</span>
              <span>{charCount.toLocaleString()} chars</span>
              {settings.model && (
                <span className="font-mono">
                  {MODEL_SHORT[settings.model] ?? settings.model}
                  {settings.temperature != null && ` · temp ${settings.temperature}`}
                  {settings.max_tokens != null &&
                    ` · ${settings.max_tokens.toLocaleString()} tokens`}
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowDiff((v) => !v)}
                disabled={!isDirty}
                className={`text-xs px-3 py-1.5 rounded border transition-colors ${
                  showDiff
                    ? "bg-white/10 border-white/20 text-white"
                    : isDirty
                    ? "border-gray-700 text-gray-400 hover:text-white hover:border-gray-500"
                    : "border-gray-800 text-gray-700 cursor-not-allowed"
                }`}
              >
                {showDiff ? "Hide diff" : "Show diff"}
              </button>

              {showConfirm ? (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-amber-400">This is live. Save?</span>
                  <button
                    onClick={handleSave}
                    disabled={saving}
                    className="text-xs px-3 py-1.5 rounded bg-[#00e87a] text-black font-semibold hover:bg-[#00e87a]/90 disabled:opacity-50 transition-colors"
                  >
                    {saving ? "Saving…" : "Yes, save"}
                  </button>
                  <button
                    onClick={() => setShowConfirm(false)}
                    className="text-xs px-3 py-1.5 rounded border border-gray-700 text-gray-400 hover:text-white transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setShowConfirm(true)}
                  disabled={!isDirty || saving}
                  className={`text-xs px-4 py-1.5 rounded font-semibold transition-colors ${
                    isDirty && !saving
                      ? "bg-[#00e87a] text-black hover:bg-[#00e87a]/90"
                      : "bg-gray-800 text-gray-600 cursor-not-allowed"
                  }`}
                >
                  Save changes
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Version history panel */}
        <div className="w-64 flex-shrink-0 flex flex-col bg-[#111] border border-gray-800 rounded-xl overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-800 flex-shrink-0">
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
              Version history
            </h3>
          </div>
          <div className="flex-1 overflow-y-auto">
            {versions.length === 0 ? (
              <p className="text-xs text-gray-600 text-center py-8 px-4">
                No saved versions yet. Versions are created on each save.
              </p>
            ) : (
              <ul className="divide-y divide-gray-900">
                {versions.map((v, idx) => (
                  <li key={v.id} className="px-4 py-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="text-xs text-gray-300 truncate">
                          {idx === 0 ? (
                            <span className="text-[#00e87a] font-semibold">Current</span>
                          ) : (
                            fmtTime(v.saved_at)
                          )}
                        </p>
                        {v.label && (
                          <p className="text-xs text-gray-600 truncate mt-0.5">{v.label}</p>
                        )}
                        {v.saved_by && (
                          <p className="text-xs text-gray-700 truncate mt-0.5">{v.saved_by}</p>
                        )}
                      </div>
                      {idx > 0 && (
                        <button
                          onClick={() => handleRevert(v.id)}
                          disabled={reverting === v.id}
                          className="text-xs text-gray-500 hover:text-white whitespace-nowrap flex-shrink-0 border border-gray-800 hover:border-gray-600 px-2 py-0.5 rounded transition-colors disabled:opacity-40"
                        >
                          {reverting === v.id ? "…" : "Revert"}
                        </button>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div className="px-4 py-3 border-t border-gray-900 flex-shrink-0">
            <p className="text-xs text-gray-700 leading-relaxed">
              Reverts are non-destructive — they save the old version as a new snapshot.
            </p>
          </div>
        </div>
      </div>

      {/* Toast */}
      {toast && (
        <div
          className={`fixed bottom-6 right-6 z-50 text-sm px-4 py-3 rounded-lg border shadow-xl transition-all ${
            toast.ok
              ? "bg-[#00e87a]/10 border-[#00e87a]/40 text-[#00e87a]"
              : "bg-red-500/10 border-red-500/40 text-red-400"
          }`}
        >
          {toast.msg}
        </div>
      )}
    </div>
  );
}
