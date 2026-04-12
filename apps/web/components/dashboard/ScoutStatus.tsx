"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase";

interface Heartbeat {
  database_id: string;
  last_seen: string;
}

export default function ScoutStatus() {
  const [heartbeats, setHeartbeats] = useState<Heartbeat[]>([]);

  useEffect(() => {
    const supabase = createClient();

    async function fetch() {
      const { data } = await supabase
        .from("scout_heartbeat")
        .select("database_id, last_seen");
      setHeartbeats(data ?? []);
    }

    fetch();
    const interval = setInterval(fetch, 30_000);
    return () => clearInterval(interval);
  }, []);

  function isAlive(lastSeen: string): boolean {
    return Date.now() - new Date(lastSeen).getTime() < 60_000;
  }

  if (heartbeats.length === 0) return null;

  return (
    <div className="flex gap-3 flex-wrap">
      {heartbeats.map((hb) => {
        const alive = isAlive(hb.last_seen);
        return (
          <div
            key={hb.database_id}
            className="flex items-center gap-2 px-3 py-1.5 bg-[#111] border border-gray-800 rounded-full text-xs"
          >
            <span
              className={`w-2 h-2 rounded-full ${alive ? "bg-[#00e87a] animate-pulse" : "bg-red-400"}`}
            />
            <span className="text-gray-400">
              Scout {alive ? "active" : "offline"}
            </span>
          </div>
        );
      })}
    </div>
  );
}
