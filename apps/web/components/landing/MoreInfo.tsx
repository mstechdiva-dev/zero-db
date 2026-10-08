"use client";

import { useState } from "react";
import Value from "./Value";
import Customer from "./Customer";
import Market from "./Market";
import Founder from "./Founder";

const CARDS = [
  { id: "value", label: "Business value", line: "One bad schema change. Hours of cleanup.", View: Value },
  { id: "customer", label: "Who it's for", line: "Engineering teams that can't afford surprises.", View: Customer },
  { id: "market", label: "Market", line: "Every team with a database has this problem.", View: Market },
  { id: "founder", label: "Founder", line: "Built by someone who's been in the incident.", View: Founder },
] as const;

export default function MoreInfo() {
  const [open, setOpen] = useState<string | null>(null);
  const current = CARDS.find((c) => c.id === open);

  return (
    <section className="bg-[#0a0a0a] border-t border-white/[0.06] px-5 sm:px-10 py-16">
      <div className="max-w-[1100px] mx-auto">
        <p className="font-mono text-[11px] text-white/22 uppercase tracking-[0.8px] mb-5">
          Learn more
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {CARDS.map((c) => {
            const active = c.id === open;
            return (
              <button
                key={c.id}
                type="button"
                aria-expanded={active}
                onClick={() => setOpen(active ? null : c.id)}
                className={`text-left bg-[#111] border rounded-xl px-5 py-4 transition-colors ${
                  active
                    ? "border-[rgba(0,232,122,0.2)]"
                    : "border-white/[0.06] hover:border-white/[0.15]"
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-mono text-[10px] text-[#00e87a] uppercase tracking-[0.8px]">
                    {c.label}
                  </span>
                  <span className="text-white/35 text-sm">{active ? "−" : "+"}</span>
                </div>
                <p className="text-[14px] text-white/70 leading-[1.4]">{c.line}</p>
              </button>
            );
          })}
        </div>

        {current && (
          <div className="mt-6 bg-[#0a0a0a] border border-white/[0.06] rounded-2xl overflow-hidden">
            <current.View />
          </div>
        )}
      </div>
    </section>
  );
}
