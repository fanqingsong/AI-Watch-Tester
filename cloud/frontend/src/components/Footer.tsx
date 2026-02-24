import Link from "next/link";
import { getTranslations } from "next-intl/server";

export default async function Footer() {
  const t = await getTranslations("footer");

  return (
    <footer className="bg-gray-900 px-4 py-6">
      <div className="mx-auto flex max-w-5xl flex-col items-center gap-2 text-xs text-gray-400 sm:flex-row sm:justify-between">
        <span>&copy; {new Date().getFullYear()} AWT. All rights reserved.</span>
        <div className="flex gap-4">
          <Link href="/terms" className="hover:text-white transition">
            {t("terms")}
          </Link>
          <Link href="/privacy" className="hover:text-white transition">
            {t("privacy")}
          </Link>
        </div>
      </div>
    </footer>
  );
}
