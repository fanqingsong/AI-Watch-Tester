"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { API_URL } from "@/lib/api";

/**
 * Pings the backend /health endpoint on mount.
 * If the response takes longer than SHOW_DELAY_MS, displays a top banner
 * informing the user the server is waking up (Render cold start).
 * Automatically hides once the server responds.
 */
const SHOW_DELAY_MS = 3000;

export default function ServerWarmup() {
  const t = useTranslations("common");
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    let dismissed = false;

    // Show banner after delay if still waiting
    const timer = setTimeout(() => {
      if (!dismissed) setVisible(true);
    }, SHOW_DELAY_MS);

    fetch(`${API_URL}/health`, { cache: "no-store" })
      .then(() => {
        dismissed = true;
        setVisible(false);
      })
      .catch(() => {
        // Server unreachable — keep banner visible, retry
        if (!dismissed) setVisible(true);
      })
      .finally(() => clearTimeout(timer));

    return () => {
      dismissed = true;
      clearTimeout(timer);
    };
  }, []);

  if (!visible) return null;

  return (
    <div className="fixed top-0 left-0 right-0 z-50 flex items-center justify-center gap-2 bg-amber-50 border-b border-amber-200 px-4 py-2 text-sm text-amber-800">
      <svg
        className="h-4 w-4 animate-spin text-amber-600"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
      >
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
      {t("serverStarting")}
    </div>
  );
}
