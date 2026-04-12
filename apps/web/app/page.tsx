"use client";

import { useState } from "react";
import Nav from "@/components/landing/Nav";
import Hero from "@/components/landing/Hero";
import HowItWorks from "@/components/landing/HowItWorks";
import Security from "@/components/landing/Security";
import Pricing from "@/components/landing/Pricing";
import type { Tab } from "@/lib/types";

export default function LandingPage() {
  const [activeTab, setActiveTab] = useState<Tab>("demo");

  return (
    <main className="min-h-screen bg-[#0a0a0a]">
      <Nav activeTab={activeTab} onTabChange={setActiveTab} />
      <div className="max-w-7xl mx-auto px-6 pb-24">
        {activeTab === "demo" && <Hero />}
        {activeTab === "how" && <HowItWorks />}
        {activeTab === "security" && <Security />}
        {activeTab === "pricing" && <Pricing />}
      </div>
    </main>
  );
}
