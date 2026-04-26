"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase";
import RiskBadge from "./RiskBadge";
import type { ChangeEvent } from "./ChangeCard";

interface ImpactAnalysis {
  summary: string;
  affected_queries: unknown[];
  affected_services: unknown[];
  affected_indexes: unknown[];
  recommendations: unknown[];
}

interface Props {
  event: ChangeEvent | null;
  onClose: () => void;
}

function JsonBlock({ data }: { data: unknown }) {
  if (data === null || data === undefined) {
    return <span className="text-gray-600 italic">none</span>;
  }
  return (
    <pre className="text-xs font-mono text-gray-300 whitespace-pre-wrap break-all bg-[#0a0a0a] rounded-lg p-3 border border-gray-900 overflow-auto max-h-48">
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}

function StringList({ items, empty }: { items: unknown[]; empty: string }) {
  if (!items || items.length === 0) {
    return <p className="text-gray-600 text-xs italic">{empty}</p>;
  }
  return (
    <ul className="space-y-1">
      {items.map((item, i) => (
        <li key={i} className="text-xs text-gray-400 font-mono bg-[#0a0a0a] rounded px-2 py-1 border border-gray-900">
          {typeof item === "string" ? item : JSON.stringify(item)}
        </li>
      ))}
    </ul>
  );
}

export default function ChangeDetailDrawer({ event, onClose }: Props) {
  const [impact, setImpact] = useState<ImpactAnalysis | null>(null);
  const [loadingImpact, setLoadingImpact] = useState(false);

  useEffect(() => {
    if (!event) {
      setImpact(null);
      return;
    }
    setLoadingImpact(true);
    const supabase = createClient();
    supabase
      .from("impact_analysis")
      .select("summary, affected_queries, affected_services, affected_indexes, recommendations")
      .eq("change_event_id", event.id)
      .single()
      .then(({ data }) => {
        setImpact(data ?? null);
        setLoadingImpact(false);
      });
  }, [event?.id]);

  if (!event) return null;

  const objectPath = event.schema_name
    ? `${event.schema_name}.${event.object_name}`
    : event.object_name;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed right-0 top-0 h-full w-full max-w-xl bg-[#111] border-l border-gray-800 z-50 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-800 flex items-start justify-between gap-4 shrink-0">
          <div className="min-w-0">
            <p className="font-mono text-white text-sm truncate">{objectPath}</p>
            <p className="text-gray-500 text-xs mt-0.5 capitalize">
              {event.change_type.replace(/_/g, " ")}
            </p>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            {event.risk_level && <RiskBadge level={event.risk_level} />}
            <button
              onClick={onClose}
              className="text-gray-600 hover:text-white transition-colors text-xl leading-none"
              aria-label="Close"
            >
              ×
            </button>
          </div>
        </div>

        {/* Scrollable body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
          {/* Meta */}
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="bg-[#0a0a0a] rounded-lg p-3 border border-gray-900">
              <p className="text-gray-600 uppercase tracking-wider mb-1">Object type</p>
              <p className="text-gray-300 font-mono capitalize">{event.object_type}</p>
            </div>
            <div className="bg-[#0a0a0a] rounded-lg p-3 border border-gray-900">
              <p className="text-gray-600 uppercase tracking-wider mb-1">Detected</p>
              <p className="text-gray-300 font-mono">
                {new Date(event.detected_at).toLocaleString()}
              </p>
            </div>
          </div>

          {/* Before / After */}
          <div className="space-y-3">
            <h3 className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Before</h3>
            <JsonBlock data={event.before_state} />
          </div>
          <div className="space-y-3">
            <h3 className="text-xs text-gray-500 uppercase tracking-wider font-semibold">After</h3>
            <JsonBlock data={event.after_state} />
          </div>

          {/* Impact analysis */}
          <div className="space-y-4">
            <h3 className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Impact Analysis</h3>
            {loadingImpact ? (
              <div className="h-20 bg-[#0a0a0a] rounded-lg border border-gray-900 animate-pulse" />
            ) : impact ? (
              <div className="space-y-4">
                <p className="text-sm text-gray-300 leading-relaxed">{impact.summary}</p>

                {(impact.recommendations as unknown[]).length > 0 && (
                  <div className="space-y-2">
                    <p className="text-xs text-gray-600 uppercase tracking-wider">Recommendations</p>
                    <StringList items={impact.recommendations as unknown[]} empty="None" />
                  </div>
                )}

                {(impact.affected_queries as unknown[]).length > 0 && (
                  <div className="space-y-2">
                    <p className="text-xs text-gray-600 uppercase tracking-wider">Affected queries</p>
                    <StringList items={impact.affected_queries as unknown[]} empty="None" />
                  </div>
                )}

                {(impact.affected_services as unknown[]).length > 0 && (
                  <div className="space-y-2">
                    <p className="text-xs text-gray-600 uppercase tracking-wider">Affected services</p>
                    <StringList items={impact.affected_services as unknown[]} empty="None" />
                  </div>
                )}

                {(impact.affected_indexes as unknown[]).length > 0 && (
                  <div className="space-y-2">
                    <p className="text-xs text-gray-600 uppercase tracking-wider">Affected indexes</p>
                    <StringList items={impact.affected_indexes as unknown[]} empty="None" />
                  </div>
                )}
              </div>
            ) : (
              <p className="text-gray-600 text-xs italic">No impact analysis available for this change.</p>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
