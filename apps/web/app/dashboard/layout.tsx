import Sidebar from "@/components/dashboard/Sidebar";
import TrialBanner from "@/components/shared/TrialBanner";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-[#0a0a0a] flex">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TrialBanner />
        <main className="flex-1 p-8">{children}</main>
      </div>
    </div>
  );
}
