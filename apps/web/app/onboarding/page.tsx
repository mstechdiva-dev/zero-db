"use client";

import { useRouter } from "next/navigation";
import ChatWindow from "@/components/onboarding/ChatWindow";
import ConnectForm from "@/components/onboarding/ConnectForm";

export default function OnboardingPage() {
  const router = useRouter();

  return (
    <main className="min-h-screen bg-[#0a0a0a] flex flex-col items-center justify-center px-6 py-10">
      <div className="w-full max-w-5xl">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white">Connect your first database</h1>
          <p className="text-gray-400 mt-2">
            Obi can help you find your connection string. Paste it into the secure box, not the
            chat.
          </p>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-[3fr_2fr] gap-6 items-start">
          <ChatWindow agentName="obi" />
          <ConnectForm onConnected={() => router.push("/dashboard")} />
        </div>
      </div>
    </main>
  );
}
