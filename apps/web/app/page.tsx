"use client";

import { useState } from "react";
import Nav from "@/components/landing/Nav";
import Hero from "@/components/landing/Hero";
import LiveDemo from "@/components/landing/LiveDemo";
import MoreInfo from "@/components/landing/MoreInfo";
import Waitlist from "@/components/landing/Waitlist";
import HowItWorks from "@/components/landing/HowItWorks";
import Security from "@/components/landing/Security";
import Pricing from "@/components/landing/Pricing";
import type { Tab } from "@/lib/types";

export default function LandingPage() {
  const [activeTab, setActiveTab] = useState<Tab>("demo");

  return (
    <main className="min-h-screen bg-[#0a0a0a]">
      <Nav activeTab={activeTab} onTabChange={setActiveTab} />
      {activeTab === "demo" && (
        <>
          <Hero onTabChange={setActiveTab} />
          <LiveDemo />
          <MoreInfo />
          <Waitlist id="waitlist" />
        </>
      )}
      {activeTab !== "demo" && (
        <div className="max-w-[960px] mx-auto px-5 sm:px-10 pb-24">
          {activeTab === "how" && <HowItWorks />}
          {activeTab === "security" && <Security />}
          {activeTab === "pricing" && <Pricing onTabChange={setActiveTab} />}
        </div>
      )}
    </main>
  );
}
