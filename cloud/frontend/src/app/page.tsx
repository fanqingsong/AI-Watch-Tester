import Link from "next/link";
import Image from "next/image";
import { getTranslations } from "next-intl/server";
import HeroAnimation from "@/components/HeroAnimation";

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "AWT - AI Watch Tester",
  description:
    "AI-powered E2E testing tool with self-healing DevQA loop. Scans your site, generates test scenarios, executes with Playwright, and auto-fixes failures.",
  applicationCategory: "DeveloperApplication",
  operatingSystem: "Web, macOS, Linux, Windows",
  offers: [
    { "@type": "Offer", price: "0", priceCurrency: "USD", name: "Open Source" },
  ],
};

const YAML_EXAMPLE = `id: "SC-002"
name: "User Login"
steps:
  - step: 1
    action: navigate
    value: "{{url}}/login"

  - step: 2
    action: find_and_type
    target:
      text: "Email"
      match_method: ocr
    value: "test@example.com"
    humanize: true

  - step: 3
    action: find_and_click
    target:
      text: "Login"

  - step: 4
    action: assert
    assert_type: text_visible
    expected:
      - type: text_visible
        value: "Welcome back"`;

const TECH_STACK = [
  { name: "Playwright", desc: "Browser automation" },
  { name: "OpenCV", desc: "Visual matching" },
  { name: "Pytesseract", desc: "OCR engine" },
  { name: "OpenAI", desc: "GPT-4o Vision" },
  { name: "Claude", desc: "Anthropic AI" },
  { name: "DeepSeek", desc: "Cost-optimized" },
  { name: "Ollama", desc: "Local LLM" },
  { name: "FastAPI", desc: "Cloud backend" },
  { name: "Next.js", desc: "Frontend" },
  { name: "Supabase", desc: "Auth & DB" },
  { name: "PostgreSQL", desc: "Cloud storage" },
  { name: "SQLite", desc: "Learning DB" },
];

export default async function LandingPage() {
  const t = await getTranslations("landing");

  return (
    <div className="overflow-x-hidden">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      {/* ═══════════════════════════════════════════════════════════════ */}
      {/* HERO                                                          */}
      {/* ═══════════════════════════════════════════════════════════════ */}
      <section className="relative bg-gradient-to-b from-blue-50 via-white to-white px-4 pb-24 pt-20 sm:pt-28">
        <div className="relative z-10 mx-auto max-w-6xl">
          <div className="grid grid-cols-1 items-center gap-12 lg:grid-cols-2">
            {/* Left: copy */}
            <div className="text-center lg:text-left">
              <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-gray-200 bg-gray-100 px-3 py-1 text-xs text-gray-500 backdrop-blur">
                <span className="h-1.5 w-1.5 rounded-full bg-green-400 animate-pulse" />
                Open Source &middot; MIT License
              </div>
              <h1 className="mb-2 text-4xl font-bold tracking-tight text-gray-900 sm:text-5xl lg:text-6xl">
                {t("heroTitle")}
              </h1>
              <p className="mb-3 font-mono text-lg text-blue-600 sm:text-xl">
                {t("heroSub")}
              </p>
              <p className="mx-auto mb-8 max-w-lg text-base leading-relaxed text-gray-500 lg:mx-0">
                {t("heroDesc")}
              </p>
              <div className="flex flex-col items-center gap-3 sm:flex-row lg:justify-start">
                <Link
                  href="/signup"
                  className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-600/20 transition hover:bg-blue-700 hover:shadow-blue-600/30 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {t("heroCta1")}
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                  </svg>
                </Link>
                <a
                  href="https://github.com/ksgisang/AI-Watch-Tester"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-gray-100 px-6 py-3 text-sm font-medium text-gray-700 transition hover:bg-gray-100 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-300"
                >
                  <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
                  </svg>
                  {t("heroCta2")}
                </a>
              </div>
            </div>

            {/* Right: terminal */}
            <HeroAnimation />
          </div>
        </div>

        {/* Gradient fade to next section */}
        <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-white to-transparent" />
      </section>

      {/* ═══════════════════════════════════════════════════════════════ */}
      {/* DEMO GIF                                                      */}
      {/* ═══════════════════════════════════════════════════════════════ */}
      <section className="px-4 py-20">
        <div className="mx-auto max-w-4xl text-center">
          <h2 className="mb-3 text-2xl font-bold text-gray-900 sm:text-3xl">
            {t("demoTitle")}
          </h2>
          <p className="mb-10 text-sm text-gray-500">
            {t("demoDesc")}
          </p>
          <div className="relative mx-auto overflow-hidden rounded-xl border border-gray-200 shadow-2xl shadow-gray-200/80">
            <div className="flex items-center gap-2 border-b border-gray-200 bg-gray-900 px-4 py-2">
              <div className="flex gap-1.5">
                <div className="h-2.5 w-2.5 rounded-full bg-red-500/70" />
                <div className="h-2.5 w-2.5 rounded-full bg-yellow-500/70" />
                <div className="h-2.5 w-2.5 rounded-full bg-green-500/70" />
              </div>
              <span className="ml-2 font-mono text-[11px] text-gray-400">AWT Cloud — Live Demo</span>
            </div>
            <Image
              src="/demo.gif"
              alt="AWT Demo — AI scanning and testing a website"
              width={960}
              height={802}
              className="w-full"
              unoptimized
              priority
            />
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════ */}
      {/* DEVQA LOOP                                                    */}
      {/* ═══════════════════════════════════════════════════════════════ */}
      <section className="px-4 py-20">
        <div className="mx-auto max-w-5xl">
          <div className="mb-16 text-center">
            <span className="mb-3 inline-block font-mono text-xs uppercase tracking-widest text-blue-600">
              Core Architecture
            </span>
            <h2 className="mb-4 text-3xl font-bold text-gray-900 sm:text-4xl">
              {t("loopTitle")}
            </h2>
            <p className="mx-auto max-w-2xl text-base text-gray-500">
              {t("loopDesc")}
            </p>
          </div>

          {/* Loop steps */}
          <div className="relative grid grid-cols-1 gap-4 sm:grid-cols-5">
            {/* Connecting line (desktop) */}
            <div className="absolute top-12 left-[10%] right-[10%] hidden h-px bg-gradient-to-r from-blue-200 via-blue-300 to-green-200 sm:block" />

            {[
              { num: "01", key: "loopStep1", descKey: "loopStep1Desc", color: "blue",
                svg: <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 15.803a7.5 7.5 0 0010.607 0z" /></svg> },
              { num: "02", key: "loopStep2", descKey: "loopStep2Desc", color: "blue",
                svg: <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25z" /></svg> },
              { num: "03", key: "loopStep3", descKey: "loopStep3Desc", color: "blue",
                svg: <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg> },
              { num: "04", key: "loopStep4", descKey: "loopStep4Desc", color: "blue",
                svg: <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z" /></svg> },
              { num: "05", key: "loopStep5", descKey: "loopStep5Desc", color: "green",
                svg: <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" /></svg> },
            ].map((step) => (
              <div key={step.num} className="relative flex flex-col items-center text-center">
                <div className={`relative z-10 mb-3 flex h-14 w-14 items-center justify-center rounded-xl border
                  ${step.color === "green"
                    ? "border-green-200 bg-green-50 text-green-600"
                    : "border-blue-200 bg-blue-50 text-blue-600"
                  }`}
                >
                  {step.svg}
                </div>
                <span className="mb-1 font-mono text-[11px] uppercase tracking-widest text-gray-400">
                  Step {step.num}
                </span>
                <h3 className="mb-2 text-sm font-semibold text-gray-800">
                  {t(step.key)}
                </h3>
                <p className="text-xs leading-relaxed text-gray-400">
                  {t(step.descKey)}
                </p>
                {step.num === "05" && (
                  <span className="mt-2 inline-block rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-600 ring-1 ring-amber-200">
                    {t("loopComingSoon")}
                  </span>
                )}
              </div>
            ))}
          </div>

          {/* Loop arrow */}
          <div className="mt-6 flex justify-center">
            <div className="flex items-center gap-2 rounded-full border border-gray-200 bg-gray-100 px-4 py-2 text-xs text-gray-500">
              <svg className="h-4 w-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              {t("loopFeedback")}
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════ */}
      {/* YAML EXAMPLE                                                  */}
      {/* ═══════════════════════════════════════════════════════════════ */}
      <section className="px-4 py-20">
        <div className="mx-auto max-w-5xl">
          <div className="grid grid-cols-1 items-center gap-10 lg:grid-cols-2">
            {/* Left: code block */}
            <div className="relative">
              <div className="absolute -inset-2 rounded-xl bg-blue-100/50 blur-xl" />
              <div className="relative overflow-hidden rounded-xl border border-gray-200 bg-gray-900">
                <div className="flex items-center justify-between border-b border-gray-200 px-4 py-2">
                  <span className="font-mono text-[11px] text-gray-400">scenario.yaml</span>
                  <span className="rounded bg-blue-50 px-2 py-0.5 text-[11px] font-medium text-blue-600 ring-1 ring-blue-200">
                    {t("diff1Badge")}
                  </span>
                </div>
                <pre className="overflow-x-auto p-4 font-mono text-[12px] leading-relaxed">
                  <code>
                    {YAML_EXAMPLE.split("\n").map((line, i) => {
                      let color = "text-gray-500";
                      if (line.match(/^\s*-\s/)) color = "text-gray-400";
                      if (line.match(/^\w/)) color = "text-blue-600";
                      if (line.includes(":") && !line.includes("//")) {
                        const [key, ...rest] = line.split(":");
                        return (
                          <span key={i} className="block">
                            <span className="text-blue-500">{key}</span>
                            <span className="text-gray-400">:</span>
                            <span className="text-green-600/80">{rest.join(":")}</span>
                          </span>
                        );
                      }
                      return <span key={i} className={`block ${color}`}>{line || "\u00A0"}</span>;
                    })}
                  </code>
                </pre>
              </div>
            </div>

            {/* Right: description */}
            <div>
              <span className="mb-3 inline-block font-mono text-xs uppercase tracking-widest text-blue-600">
                {t("diff1Badge")}
              </span>
              <h2 className="mb-4 text-2xl font-bold text-gray-900 sm:text-3xl">
                {t("yamlTitle")}
              </h2>
              <p className="mb-6 text-base leading-relaxed text-gray-500">
                {t("yamlDesc")}
              </p>
              <ul className="mb-8 space-y-3 text-sm text-gray-500">
                {(["yamlFeat1", "yamlFeat2", "yamlFeat3", "yamlFeat4"] as const).map((key) => (
                  <li key={key} className="flex items-start gap-2">
                    <span className="mt-1 text-blue-600">→</span>
                    <span>{t(key)}</span>
                  </li>
                ))}
              </ul>

              {/* Natural language → YAML */}
              <div className="rounded-xl border border-blue-200 bg-blue-50/50 p-5">
                <div className="mb-2 flex items-center gap-2">
                  <svg className="h-5 w-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
                  </svg>
                  <h3 className="text-sm font-semibold text-gray-900">{t("yamlNlTitle")}</h3>
                </div>
                <p className="mb-3 text-xs text-gray-500">{t("yamlNlDesc")}</p>
                <div className="rounded-lg bg-white border border-gray-200 px-3 py-2.5 text-sm italic text-gray-600">
                  {t("yamlNlExample")}
                </div>
                <p className="mt-2 font-mono text-xs font-medium text-blue-600">{t("yamlNlResult")}</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════ */}
      {/* 4 DIFFERENTIATORS                                             */}
      {/* ═══════════════════════════════════════════════════════════════ */}
      <section className="px-4 py-20">
        <div className="mx-auto max-w-5xl">
          <div className="mb-12 text-center">
            <span className="mb-3 inline-block font-mono text-xs uppercase tracking-widest text-blue-600">
              Differentiators
            </span>
            <h2 className="mb-4 text-3xl font-bold text-gray-900 sm:text-4xl">
              {t("diffTitle")}
            </h2>
            <p className="text-base text-gray-500">{t("diffDesc")}</p>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {[
              {
                titleKey: "diff1Title", descKey: "diff1Desc", badgeKey: "diff1Badge",
                icon: (
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                  </svg>
                ),
              },
              {
                titleKey: "diff2Title", descKey: "diff2Desc", badgeKey: "diff2Badge",
                soonKey: "diff2Soon",
                icon: (
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" />
                  </svg>
                ),
              },
              {
                titleKey: "diff3Title", descKey: "diff3Desc", badgeKey: "diff3Badge",
                icon: (
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                ),
              },
              {
                titleKey: "diff4Title", descKey: "diff4Desc", badgeKey: "diff4Badge",
                icon: (
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4.26 10.147a60.436 60.436 0 00-.491 6.347A48.627 48.627 0 0112 20.904a48.627 48.627 0 018.232-4.41 60.46 60.46 0 00-.491-6.347m-15.482 0a50.57 50.57 0 00-2.658-.813A59.905 59.905 0 0112 3.493a59.902 59.902 0 0110.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.697 50.697 0 0112 13.489a50.702 50.702 0 017.74-3.342" />
                  </svg>
                ),
              },
            ].map((card) => (
              <div
                key={card.titleKey}
                className="group rounded-xl border border-gray-200 bg-white p-6 transition hover:border-gray-300 hover:bg-gray-100"
              >
                <div className="mb-4 flex items-center justify-between">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-blue-600 ring-1 ring-blue-200">
                    {card.icon}
                  </div>
                  <span className="rounded-full bg-gray-100 px-2.5 py-0.5 text-[11px] font-medium text-gray-500 ring-1 ring-gray-200">
                    {t(card.badgeKey)}
                  </span>
                </div>
                <h3 className="mb-2 text-lg font-semibold text-gray-900">
                  {t(card.titleKey)}
                </h3>
                <p className="text-sm leading-relaxed text-gray-500">
                  {t(card.descKey)}
                </p>
                {card.soonKey && (
                  <span className="mt-3 inline-block rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-600 ring-1 ring-amber-200">
                    {t(card.soonKey)}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════ */}
      {/* MORE FEATURES (8 cards grid)                                  */}
      {/* ═══════════════════════════════════════════════════════════════ */}
      <section className="px-4 py-20">
        <div className="mx-auto max-w-5xl">
          <div className="mb-12 text-center">
            <span className="mb-3 inline-block font-mono text-xs uppercase tracking-widest text-blue-600">
              Features
            </span>
            <h2 className="mb-4 text-2xl font-bold text-gray-900 sm:text-3xl">
              {t("featTitle")}
            </h2>
            <p className="text-sm text-gray-500">{t("featDesc")}</p>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {[
              { key: "feat1", svg: <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M15.042 21.672L13.684 16.6m0 0l-2.51 2.225.569-9.47 5.227 7.917-3.286-.672zM12 2.25V4.5m5.834.166l-1.591 1.591M20.25 10.5H18M7.757 14.743l-1.59 1.59M6 10.5H3.75m4.007-4.243l-1.59-1.59" /></svg> },
              { key: "feat2", svg: <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15" /></svg> },
              { key: "feat3", svg: <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" /></svg> },
              { key: "feat4", svg: <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" /></svg> },
              { key: "feat5", svg: <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" /></svg> },
              { key: "feat6", svg: <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M10.5 21l5.25-11.25L21 21m-9-3h7.5M3 5.621a48.474 48.474 0 016-.371m0 0c1.12 0 2.233.038 3.334.114M9 5.25V3m3.334 2.364C11.176 10.658 7.69 15.08 3 17.502m9.334-12.138c.896.061 1.785.147 2.666.257m-4.589 8.495a18.023 18.023 0 01-3.827-5.802" /></svg> },
              { key: "feat7", svg: <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M9 17.25v1.007a3 3 0 01-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0115 18.257V17.25m6-12V15a2.25 2.25 0 01-2.25 2.25H5.25A2.25 2.25 0 013 15V5.25m18 0A2.25 2.25 0 0018.75 3H5.25A2.25 2.25 0 003 5.25m18 0V12a2.25 2.25 0 01-2.25 2.25H5.25A2.25 2.25 0 013 12V5.25" /></svg> },
              { key: "feat8", svg: <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M7.217 10.907a2.25 2.25 0 100 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186l9.566-5.314m-9.566 7.5l9.566 5.314m0 0a2.25 2.25 0 103.935 2.186 2.25 2.25 0 00-3.935-2.186zm0-12.814a2.25 2.25 0 103.933-2.185 2.25 2.25 0 00-3.933 2.185z" /></svg> },
            ].map((f) => (
              <div
                key={f.key}
                className="rounded-lg border border-gray-200 bg-white p-4 transition hover:border-gray-300 hover:shadow-sm"
              >
                <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
                  {f.svg}
                </div>
                <h3 className="mb-1 text-sm font-semibold text-gray-800">
                  {t(`${f.key}Title`)}
                </h3>
                <p className="text-xs leading-relaxed text-gray-500">
                  {t(`${f.key}Desc`)}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════ */}
      {/* COST OPTIMIZATION                                             */}
      {/* ═══════════════════════════════════════════════════════════════ */}
      <section className="px-4 py-20">
        <div className="mx-auto max-w-5xl">
          <div className="mb-12 text-center">
            <span className="mb-3 inline-block font-mono text-xs uppercase tracking-widest text-blue-600">
              Economics
            </span>
            <h2 className="mb-4 text-2xl font-bold text-gray-900 sm:text-3xl">
              {t("costTitle")}
            </h2>
            <p className="text-sm text-gray-500">{t("costDesc")}</p>
          </div>

          {/* Stats */}
          <div className="mb-10 grid grid-cols-1 gap-4 sm:grid-cols-3">
            {[
              { statKey: "costStat1", labelKey: "costStat1Label" },
              { statKey: "costStat2", labelKey: "costStat2Label" },
              { statKey: "costStat3", labelKey: "costStat3Label" },
            ].map((s) => (
              <div
                key={s.statKey}
                className="rounded-xl border border-gray-200 bg-white p-6 text-center"
              >
                <div className="mb-1 font-mono text-2xl font-bold text-blue-600 ">
                  {t(s.statKey)}
                </div>
                <div className="text-xs text-gray-400">{t(s.labelKey)}</div>
              </div>
            ))}
          </div>

          {/* Feature list */}
          <div className="mx-auto max-w-2xl rounded-xl border border-gray-200 bg-gray-50 p-6">
            <ul className="space-y-3">
              {["costFeat1", "costFeat2", "costFeat3", "costFeat4"].map((key) => (
                <li key={key} className="flex items-start gap-3 text-sm text-gray-500">
                  <span className="mt-0.5 font-mono text-green-600">✓</span>
                  {t(key)}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════ */}
      {/* SKILL MODE vs CLI MODE                                        */}
      {/* ═══════════════════════════════════════════════════════════════ */}
      <section className="bg-gray-50 px-4 py-20">
        <div className="mx-auto max-w-5xl">
          <div className="mb-12 text-center">
            <span className="mb-3 inline-block font-mono text-xs uppercase tracking-widest text-blue-600">
              Modes
            </span>
            <h2 className="mb-4 text-2xl font-bold text-gray-900 sm:text-3xl">
              {t("skillTitle")}
            </h2>
            <p className="text-sm text-gray-500">{t("skillDesc")}</p>
          </div>

          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            {/* Skill Mode — highlighted */}
            <div className="relative flex flex-col rounded-xl border-2 border-blue-500 bg-blue-50/30 p-6">
              <span className="absolute -top-3 left-4 rounded-full bg-blue-600 px-3 py-0.5 text-xs font-bold text-white">
                {t("skillModeBadge")}
              </span>
              <h3 className="mb-2 text-lg font-bold text-gray-900">{t("skillModeTitle")}</h3>
              <p className="mb-4 text-sm text-gray-500">{t("skillModeDesc")}</p>
              <ul className="flex-1 space-y-2">
                {["skillModeFeat1", "skillModeFeat2", "skillModeFeat3", "skillModeFeat4", "skillModeFeat5"].map((key) => (
                  <li key={key} className="flex items-start gap-2 text-sm text-gray-600">
                    <span className="mt-0.5 text-blue-600">✓</span>
                    {t(key)}
                  </li>
                ))}
              </ul>
            </div>

            {/* CLI Mode */}
            <div className="flex flex-col rounded-xl border border-gray-200 bg-white p-6">
              <h3 className="mb-2 text-lg font-bold text-gray-900">{t("cliModeTitle")}</h3>
              <p className="mb-4 text-sm text-gray-500">{t("cliModeDesc")}</p>
              <ul className="flex-1 space-y-2">
                {["cliModeFeat1", "cliModeFeat2", "cliModeFeat3", "cliModeFeat4", "cliModeFeat5"].map((key) => (
                  <li key={key} className="flex items-start gap-2 text-sm text-gray-600">
                    <span className="mt-0.5 text-green-600">✓</span>
                    {t(key)}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════ */}
      {/* TECH STACK                                                    */}
      {/* ═══════════════════════════════════════════════════════════════ */}
      <section className="px-4 py-20">
        <div className="mx-auto max-w-5xl">
          <div className="mb-10 text-center">
            <span className="mb-3 inline-block font-mono text-xs uppercase tracking-widest text-blue-600">
              Stack
            </span>
            <h2 className="mb-4 text-2xl font-bold text-gray-900 sm:text-3xl">
              {t("techTitle")}
            </h2>
          </div>

          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
            {TECH_STACK.map((tech) => (
              <div
                key={tech.name}
                className="flex flex-col items-center rounded-lg border border-gray-200 bg-gray-50 p-3 text-center transition hover:border-gray-300"
              >
                <span className="font-mono text-xs font-medium text-gray-700">{tech.name}</span>
                <span className="text-[11px] text-gray-400">{tech.desc}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════ */}
      {/* PRICING                                                       */}
      {/* ═══════════════════════════════════════════════════════════════ */}
      <section className="px-4 py-20">
        <div className="mx-auto max-w-4xl">
          <div className="mb-12 text-center">
            <span className="mb-3 inline-block font-mono text-xs uppercase tracking-widest text-blue-600">
              Plans
            </span>
            <h2 className="mb-4 text-2xl font-bold text-gray-900 sm:text-3xl">
              {t("pricingTitle")}
            </h2>
          </div>

          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
            {/* Free */}
            <div className="flex flex-col rounded-xl border border-gray-200 bg-white p-6">
              <h3 className="mb-1 text-lg font-bold text-gray-900">{t("pricingFreeTitle")}</h3>
              <div className="mb-1">
                <span className="font-mono text-3xl font-bold text-gray-900">{t("pricingFreePrice")}</span>
              </div>
              <p className="mb-6 text-sm text-gray-500">{t("pricingFreeDesc")}</p>
              <ul className="mb-8 flex-1 space-y-2.5">
                {["pricingFreeFeat1", "pricingFreeFeat2", "pricingFreeFeat3", "pricingFreeFeat4"].map((key) => (
                  <li key={key} className="flex items-start gap-2 text-sm text-gray-600">
                    <span className="mt-0.5 text-green-600">✓</span>
                    {t(key)}
                  </li>
                ))}
              </ul>
              <Link
                href="/signup"
                className="block rounded-lg border border-gray-300 py-2.5 text-center text-sm font-medium text-gray-700 transition hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-300"
              >
                {t("pricingFreeCta")}
              </Link>
            </div>

            {/* Pro — highlighted */}
            <div className="relative flex flex-col rounded-xl border-2 border-blue-500 bg-blue-50/30 p-6">
              <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-blue-600 px-3 py-0.5 text-[11px] font-bold text-white whitespace-nowrap">
                {t("pricingProBadge")}
              </span>
              <h3 className="mb-1 text-lg font-bold text-gray-900">{t("pricingProTitle")}</h3>
              <div className="mb-1">
                <span className="font-mono text-3xl font-bold text-gray-900">{t("pricingProPrice")}</span>
                <span className="text-sm text-gray-500">{t("pricingPerMonth")}</span>
              </div>
              <p className="mb-6 text-sm text-gray-500">{t("pricingProDesc")}</p>
              <ul className="mb-8 flex-1 space-y-2.5">
                {["pricingProFeat1", "pricingProFeat2", "pricingProFeat3", "pricingProFeat4", "pricingProFeat5"].map((key) => (
                  <li key={key} className="flex items-start gap-2 text-sm text-gray-600">
                    <span className="mt-0.5 text-blue-600">✓</span>
                    {t(key)}
                  </li>
                ))}
              </ul>
              <Link
                href="/pricing"
                className="block rounded-lg bg-blue-600 py-2.5 text-center text-sm font-semibold text-white transition hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {t("pricingProCta")}
              </Link>
            </div>

            {/* Team */}
            <div className="flex flex-col rounded-xl border border-gray-200 bg-white p-6">
              <h3 className="mb-1 text-lg font-bold text-gray-900">{t("pricingTeamTitle")}</h3>
              <div className="mb-1">
                <span className="font-mono text-3xl font-bold text-gray-900">{t("pricingTeamPrice")}</span>
                <span className="text-sm text-gray-500">{t("pricingPerMonth")}</span>
              </div>
              <p className="mb-6 text-sm text-gray-500">{t("pricingTeamDesc")}</p>
              <ul className="mb-8 flex-1 space-y-2.5">
                {["pricingTeamFeat1", "pricingTeamFeat2", "pricingTeamFeat3", "pricingTeamFeat4"].map((key) => (
                  <li key={key} className="flex items-start gap-2 text-sm text-gray-600">
                    <span className="mt-0.5 text-green-600">✓</span>
                    {t(key)}
                  </li>
                ))}
              </ul>
              <Link
                href="/pricing"
                className="block rounded-lg border border-gray-300 py-2.5 text-center text-sm font-medium text-gray-700 transition hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-300"
              >
                {t("pricingTeamCta")}
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════ */}
      {/* FINAL CTA                                                     */}
      {/* ═══════════════════════════════════════════════════════════════ */}
      <section className="relative px-4 py-20">
        <div className="absolute inset-0 bg-blue-50/30 opacity-50" />
        <div className="relative mx-auto max-w-3xl text-center">
          <h2 className="mb-3 text-2xl font-bold text-gray-900 sm:text-3xl">
            {t("ctaTitle")}
          </h2>
          <p className="mb-8 text-base text-gray-500">{t("ctaDesc")}</p>
          <div className="flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
            <Link
              href="/signup"
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-7 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-600/20 transition hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {t("ctaBtn1")}
            </Link>
            <a
              href="https://github.com/ksgisang/AI-Watch-Tester"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-gray-100 px-7 py-3 text-sm font-medium text-gray-700 transition hover:bg-gray-100 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-300"
            >
              <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
              </svg>
              {t("ctaBtn2")}
            </a>
          </div>
        </div>
      </section>
    </div>
  );
}
