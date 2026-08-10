import { useTranslation } from "react-i18next";
import { SUPPORTED_LANGUAGES } from "../i18n";

const LABELS: Record<string, string> = { en: "EN", ru: "RU" };

export function LanguageSwitcher() {
  const { i18n } = useTranslation();
  const current = i18n.language;

  return (
    <div className="flex overflow-hidden rounded-md border border-slate-200 text-xs font-medium">
      {SUPPORTED_LANGUAGES.map((lang) => (
        <button
          key={lang}
          type="button"
          aria-pressed={current === lang}
          onClick={() => void i18n.changeLanguage(lang)}
          className={`px-2 py-1 ${
            current === lang ? "bg-blue-600 text-white" : "bg-white text-slate-500 hover:bg-slate-50"
          }`}
        >
          {LABELS[lang]}
        </button>
      ))}
    </div>
  );
}
