"use client";

import { useRouter } from "next/navigation";
import ChatWindow from "@/components/onboarding/ChatWindow";

export default function OnboardingPage() {
  const router = useRouter();

  function handleComplete() {
    router.push("/dashboard");
  }

  return (
    <main className="min-h-screen bg-[#0a0a0a] flex flex-col items-center justify-center px-6">
      <div className="w-full max-w-2xl">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white">
            Connect your first database
          </h1>
          <p className="text-gray-400 mt-2">
            Obi will guide you through the setup.
          </p>
        </div>
        <ChatWindow agentName="obi" onComplete={handleComplete} />
      </div>
    </main>
  );
}
