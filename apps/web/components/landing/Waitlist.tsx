"use client";

import { useState } from "react";

export default function Waitlist() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email) return;
    setLoading(true);
    try {
      await fetch("/api/waitlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
    } catch {
      // fail silently — don't block the UX
    }
    setSubmitted(true);
    setLoading(false);
  }

  return (
    <section className="bg-[#0a0a0a] border-t border-white/[0.06] px-10 py-24">
      <div className="max-w-[960px] mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">

          {/* Left: waitlist */}
          <div>
            <p className="font-mono text-[11px] text-white/22 uppercase tracking-[0.8px] mb-3">
              Early access
            </p>
            <h2 className="text-3xl font-semibold text-white tracking-[-1px] leading-[1.15] mb-4">
              Launching 2026.<br />
              <span className="text-[#00e87a]">Be first in line.</span>
            </h2>
            <p className="text-base text-white/45 leading-[1.65] mb-8 max-w-[420px]">
              Join the waitlist for early access and founding member pricing.
              No credit card. No commitment.
            </p>

            {submitted ? (
              <div className="flex items-center gap-3 bg-[rgba(0,232,122,0.06)] border border-[rgba(0,232,122,0.2)] rounded-xl px-5 py-4">
                <span className="w-2 h-2 rounded-full bg-[#00e87a]" />
                <p className="text-[14px] text-[#00e87a]">
                  You're on the list. We'll be in touch.
                </p>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="flex gap-2 flex-wrap">
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@company.com"
                  className="flex-1 min-w-[220px] bg-[#111] border border-white/[0.1] rounded-lg px-4 py-3 text-sm text-white placeholder-white/25 outline-none focus:border-[rgba(0,232,122,0.4)] transition-colors"
                />
                <button
                  type="submit"
                  disabled={loading}
                  className="px-6 py-3 bg-[#00e87a] text-black text-sm font-semibold rounded-lg hover:opacity-85 transition-opacity disabled:opacity-50 whitespace-nowrap"
                >
                  {loading ? "Joining…" : "Join waitlist"}
                </button>
              </form>
            )}
          </div>

          {/* Right: investor CTA */}
          <div className="bg-[#111] border border-white/[0.06] rounded-2xl p-8">
            <p className="font-mono text-[11px] text-white/22 uppercase tracking-[0.8px] mb-4">
              Investors
            </p>
            <p className="text-[22px] font-semibold text-white tracking-[-0.6px] leading-[1.25] mb-3">
              Interested in SchemaZero?
            </p>
            <p className="text-[14px] text-white/45 leading-[1.65] mb-6">
              We're raising a pre-seed round. If database reliability tooling is in your
              thesis, we'd like to talk.
            </p>
            <div className="space-y-3">
              <a
                href="mailto:invest@schemazero.com"
                className="flex items-center justify-between w-full px-5 py-3.5 bg-[#00e87a] text-black text-sm font-semibold rounded-lg hover:opacity-85 transition-opacity"
              >
                Request investor deck
                <span className="text-base">→</span>
              </a>
              <a
                href="mailto:invest@schemazero.com"
                className="flex items-center justify-between w-full px-5 py-3.5 border border-white/[0.1] text-white/55 text-sm font-medium rounded-lg hover:text-white hover:border-white/22 transition-colors"
              >
                Book a 20-min call
                <span className="text-base">→</span>
              </a>
            </div>
          </div>

        </div>
      </div>
    </section>
  );
}
