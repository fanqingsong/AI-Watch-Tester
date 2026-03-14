"use client";

import { useState, useEffect, useRef } from "react";
import { useTranslations } from "next-intl";

const LINES = [
  { key: "heroTerminal1", type: "cmd", delay: 0 },
  { key: "heroTerminal2", type: "out", delay: 1400 },
  { key: "heroTerminal3", type: "out", delay: 2200 },
  { key: "heroTerminal4", type: "out", delay: 3000 },
  { key: "heroTerminal5", type: "success", delay: 3800 },
  { key: "heroTerminal6", type: "cmd", delay: 5000 },
  { key: "heroTerminal7", type: "out", delay: 6400 },
  { key: "heroTerminal8", type: "pass", delay: 7200 },
  { key: "heroTerminal9", type: "pass", delay: 7800 },
  { key: "heroTerminal10", type: "fail", delay: 8400 },
  { key: "heroTerminal11", type: "warn", delay: 9400 },
  { key: "heroTerminal12", type: "success", delay: 10400 },
  { key: "heroTerminal13", type: "out", delay: 11200 },
  { key: "heroTerminal14", type: "pass", delay: 12000 },
] as const;

const TOTAL_CYCLE = 15000;

export default function HeroAnimation() {
  const t = useTranslations("landing");
  const [cycle, setCycle] = useState(0);
  const [visibleCount, setVisibleCount] = useState(0);
  const [typingIdx, setTypingIdx] = useState(-1);
  const [typedText, setTypedText] = useState("");
  const [reduceMotion, setReduceMotion] = useState(false);
  const intervalsRef = useRef<ReturnType<typeof setInterval>[]>([]);

  // Detect reduced motion preference
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduceMotion(mq.matches);
    const handler = (e: MediaQueryListEvent) => setReduceMotion(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  // Main animation effect — only re-runs on cycle change
  useEffect(() => {
    if (reduceMotion) {
      setVisibleCount(LINES.length);
      return;
    }

    // Reset state for new cycle
    setVisibleCount(0);
    setTypingIdx(-1);
    setTypedText("");

    const timers: ReturnType<typeof setTimeout>[] = [];

    LINES.forEach((line, i) => {
      timers.push(
        setTimeout(() => {
          if (line.type === "cmd") {
            setTypingIdx(i);
            setTypedText("");
            const fullText = t(line.key);
            let charIdx = 0;
            const typeInterval = setInterval(() => {
              charIdx++;
              setTypedText(fullText.slice(0, charIdx));
              if (charIdx >= fullText.length) {
                clearInterval(typeInterval);
                setTimeout(() => {
                  setTypingIdx(-1);
                  setVisibleCount(i + 1);
                }, 300);
              }
            }, 30);
            intervalsRef.current.push(typeInterval);
          } else {
            setVisibleCount(i + 1);
          }
        }, line.delay)
      );
    });

    // Schedule next cycle
    timers.push(
      setTimeout(() => {
        setCycle((c) => c + 1);
      }, TOTAL_CYCLE)
    );

    return () => {
      timers.forEach(clearTimeout);
      intervalsRef.current.forEach(clearInterval);
      intervalsRef.current = [];
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cycle, reduceMotion]);

  const colorFor = (type: string) => {
    switch (type) {
      case "cmd": return "text-cyan-400";
      case "pass": return "text-green-400";
      case "fail": return "text-red-400";
      case "warn": return "text-amber-400";
      case "success": return "text-green-400";
      default: return "text-zinc-400";
    }
  };

  return (
    <div className="relative mx-auto w-full max-w-xl">
      {/* Glow behind terminal */}
      <div className="absolute -inset-4 rounded-2xl bg-cyan-500/5 blur-2xl" />

      {/* Terminal chrome */}
      <div className="relative overflow-hidden rounded-xl border border-zinc-700/60 bg-zinc-900/90 shadow-2xl shadow-black/50 backdrop-blur">
        {/* Title bar */}
        <div className="flex items-center gap-2 border-b border-zinc-800 bg-zinc-900 px-4 py-2.5">
          <div className="flex gap-1.5">
            <div className="h-3 w-3 rounded-full bg-red-500/70" />
            <div className="h-3 w-3 rounded-full bg-yellow-500/70" />
            <div className="h-3 w-3 rounded-full bg-green-500/70" />
          </div>
          <span className="ml-3 font-mono text-[11px] text-zinc-500">
            awt — zsh — 80×24
          </span>
        </div>

        {/* Terminal content */}
        <div className="h-[340px] overflow-hidden p-4 font-mono text-[13px] leading-relaxed">
          {LINES.map((line, i) => {
            if (typingIdx === i) {
              return (
                <div key={i} className={`${colorFor(line.type)} whitespace-pre`}>
                  {typedText}
                  <span className="animate-blink text-cyan-400">▊</span>
                </div>
              );
            }
            if (i < visibleCount) {
              return (
                <div
                  key={i}
                  className={`${colorFor(line.type)} whitespace-pre`}
                >
                  {t(line.key)}
                </div>
              );
            }
            return null;
          })}
          {visibleCount >= LINES.length && (
            <div className="mt-1 text-cyan-400 whitespace-pre">
              $ <span className="animate-blink">▊</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
