"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase";
import ChangeCard, { type ChangeEvent } from "./ChangeCard";

export default function ChangeFeed() {
  const [events, setEvents] = useState<ChangeEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const supabase = createClient();

    async function fetchEvents() {
      const { data } = await supabase
        .from("change_events")
        .select("*")
        .order("detected_at", { ascending: false })
        .limit(50);
      setEvents(data ?? []);
      setLoading(false);
    }

    fetchEvents();

    // Real-time subscription
    const channel = supabase
      .channel("change_events_feed")
      .on(
        "postgres_changes",
        { event: "INSERT", schema: "public", table: "change_events" },
        (payload) => {
          setEvents((prev) => [payload.new as ChangeEvent, ...prev]);
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  if (loading) {
    return (
      <div className="space-y-3">
        {[...Array(3)].map((_, i) => (
          <div
            key={i}
            className="h-20 bg-[#111] border border-gray-800 rounded-xl animate-pulse"
          />
        ))}
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <div className="bg-[#111] border border-gray-800 rounded-xl p-12 text-center">
        <p className="text-gray-500">
          No schema changes detected yet. Scout is watching.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {events.map((event) => (
        <ChangeCard key={event.id} event={event} />
      ))}
    </div>
  );
}
