import Link from "next/link";
import { getTranslations } from "next-intl/server";

export default async function Footer() {
  const t = await getTranslations("footer");

  return (
    <footer className="border-t border-gray-200 bg-gray-50">
      <div className="mx-auto max-w-6xl px-4 py-10">
        <div className="flex flex-col gap-8 sm:flex-row sm:items-start sm:justify-between">
          {/* Brand */}
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-2">
              <svg width="24" height="24" viewBox="0 0 120 120" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="60" cy="60" r="52" stroke="#0d9488" strokeWidth="8"/>
                <circle cx="52" cy="52" r="20" fill="#34d399"/>
                <circle cx="52" cy="52" r="8" fill="#f9fafb"/>
              </svg>
              <span className="text-sm font-bold text-gray-900">AWT</span>
            </div>
            <p className="text-xs text-gray-500 max-w-[260px] leading-relaxed">
              {t("tagline")}
            </p>
          </div>

          {/* Links */}
          <div className="flex gap-12 text-sm">
            <div className="flex flex-col gap-2.5">
              <span className="text-xs font-medium uppercase tracking-wider text-gray-400">{t("product")}</span>
              <Link href="/pricing" className="text-gray-600 transition hover:text-gray-900">{t("pricing")}</Link>
              <Link href="/status" className="text-gray-600 transition hover:text-gray-900">{t("status")}</Link>
              <a href="https://github.com/ksgisang/AI-Watch-Tester" target="_blank" rel="noopener noreferrer" className="text-gray-600 transition hover:text-gray-900">GitHub</a>
            </div>
            <div className="flex flex-col gap-2.5">
              <span className="text-xs font-medium uppercase tracking-wider text-gray-400">{t("legal")}</span>
              <Link href="/terms" className="text-gray-600 transition hover:text-gray-900">{t("terms")}</Link>
              <Link href="/privacy" className="text-gray-600 transition hover:text-gray-900">{t("privacy")}</Link>
            </div>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="mt-8 flex flex-col items-center gap-2 border-t border-gray-200 pt-6 sm:flex-row sm:justify-between">
          <span className="text-xs text-gray-400">
            &copy; {new Date().getFullYear()} AWT &mdash; {t("builtBy")}
          </span>
          <a
            href="https://github.com/ksgisang/AI-Watch-Tester"
            target="_blank"
            rel="noopener noreferrer"
            className="text-gray-400 transition hover:text-gray-600"
            aria-label="GitHub"
          >
            <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
            </svg>
          </a>
        </div>
      </div>
    </footer>
  );
}
