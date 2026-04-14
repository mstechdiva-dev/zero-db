"use client";

import { useState, useCallback } from "react";

interface Props {
  agentName: string;
  role: string;
  initialContent: string;
}

// Simple line diff for the diff view
type DiffLine = { type: "same" | "added" | "removed"; text: string };

function lineDiff(original: string, modified: string): DiffLine[] {
  const a = original.split("\n");
  const b = modified.split("\n");
  const result: DiffLine[] = [];
  let i = 0, j = 0;

  while (i < a.length || j < b.length) {
    if (i >= a.length) {
      result.push({ type: "added", text: b[j++] });
    } else if (j >= b.length) {
      result.push({ type: "removed", text: a[i++] });
    } else if (a[i] === b[j]) {
      result.push({ type: "same", text: a[i++] });
      j++;
    } else {
      let found = false;
      for (let k = 1; k <= 8 && !found; k++) {
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

export default function AgentEditor({ agentName, role, initialContent }: Props) {
  const [content, setContent] = useState(initialContent);
  const [savedContent, setSavedContent] = useState(initialContent);
  const [saving, setSaving] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [showDiff, setShowDiff] = useState(false);
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);

  const isDirty = content !== savedContent;

  const showToast = useCallback((msg: string, ok: boolean) => {
    setToast({ msg, ok });
    setTimeout(() => setToast(null), 3000);
  }, []);

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
      setShowDiff(false);
      showToast("Saved — live on next agent call", true);
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Save failed", false);
    } finally {
      setSaving(false);
    }
  }, [agentName, content, showToast]);

  const diff = showDiff ? lineDiff(savedContent, content) : [];

  return (
    <div className="flex flex-col h-[calc(100vh-140px)] min-h-[500px]">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 flex-shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono font-bold text-[#00e87a] uppercase tracking-widest border border-[#00e87a]/40 px-2 py-1 rounded">
            {agentName}
          </span>
          <span className="text-gray-500 text-sm truncate max-w-md">{role}</span>
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

      {/* Editor / Diff */}
      {showDiff ? (
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
            <span className="ml-auto">
              -{diff.filter((l) => l.type === "removed").length}{" "}
              +{diff.filter((l) => l.type === "added").length}
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
                <span className="select-none text-gray-700 mr-3 w-4 inline-block text-right">
                  {line.type === "removed" ? "−" : line.type === "added" ? "+" : " "}
                </span>
                {line.text}
              </div>
            ))}
          </div>
        </div>
      ) : (
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          className="flex-1 w-full bg-[#0d0d0d] border border-gray-800 rounded-xl p-5 font-mono text-xs text-gray-200 leading-5 resize-none focus:outline-none focus:border-gray-700 transition-colors"
          spellCheck={false}
        />
      )}

      {/* Footer */}
      <div className="flex items-center justify-between mt-3 flex-shrink-0">
        <span className="text-xs text-gray-700">
          {content.split("\n").length} lines · {content.length} chars
        </span>
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

      {/* Toast */}
      {toast && (
        <div
          className={`fixed bottom-6 right-6 z-50 text-sm px-4 py-3 rounded-lg border shadow-xl ${
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
