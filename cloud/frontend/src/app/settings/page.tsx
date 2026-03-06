"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { useAuth } from "@/components/AuthProvider";
import Link from "next/link";
import {
  createApiKey,
  listApiKeys,
  deleteApiKey,
  fetchBilling,
  getAIConfig,
  saveAIConfig,
  deleteAIConfig,
  testAIConfig,
  getGitHubConnection,
  saveGitHubConnection,
  deleteGitHubConnection,
  verifyGitHubConnection,
  type ApiKeyItem,
  type ApiKeyCreatedItem,
  type BillingInfo,
  type AIConfigInfo,
  type AIConfigTestResult,
  type GitHubConnectionInfo,
  type GitHubVerifyResult,
} from "@/lib/api";

export default function SettingsPage() {
  const { user } = useAuth();
  const t = useTranslations("settings");

  // API Keys state
  const [keys, setKeys] = useState<ApiKeyItem[]>([]);
  const [newKeyName, setNewKeyName] = useState("");
  const [createdKey, setCreatedKey] = useState<ApiKeyCreatedItem | null>(null);
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [billing, setBilling] = useState<BillingInfo | null>(null);

  // GitHub Connection state
  const [ghConn, setGhConn] = useState<GitHubConnectionInfo | null>(null);
  const [ghPat, setGhPat] = useState("");
  const [ghRepo, setGhRepo] = useState("");  // owner/repo format
  const [ghBranch, setGhBranch] = useState("main");
  const [showPat, setShowPat] = useState(false);
  const [ghSaving, setGhSaving] = useState(false);
  const [ghVerifying, setGhVerifying] = useState(false);
  const [ghVerifyResult, setGhVerifyResult] = useState<GitHubVerifyResult | null>(null);
  const [ghMessage, setGhMessage] = useState("");
  const [ghError, setGhError] = useState("");

  // Advanced Options state
  const [useAiPlan, setUseAiPlan] = useState(false);

  // AI Config state
  const [aiConfig, setAiConfig] = useState<AIConfigInfo | null>(null);
  const [aiProvider, setAiProvider] = useState("openai");
  const [aiApiKey, setAiApiKey] = useState("");
  const [aiModel, setAiModel] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [aiSaving, setAiSaving] = useState(false);
  const [aiTesting, setAiTesting] = useState(false);
  const [aiTestResult, setAiTestResult] = useState<AIConfigTestResult | null>(null);
  const [aiMessage, setAiMessage] = useState("");
  const [aiError, setAiError] = useState("");

  const loadKeys = async () => {
    try {
      const data = await listApiKeys();
      setKeys(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load keys");
    }
  };

  const loadGitHub = async () => {
    try {
      const conn = await getGitHubConnection();
      setGhConn(conn);
      if (conn.connected) {
        setGhRepo(`${conn.owner}/${conn.repo}`);
        setGhBranch(conn.default_branch);
      }
    } catch {
      // ignore
    }
  };

  const loadAIConfig = async () => {
    try {
      const cfg = await getAIConfig();
      setAiConfig(cfg);
      if (cfg.has_key) {
        setAiProvider(cfg.provider);
        setAiModel(cfg.model);
      }
    } catch {
      // ignore — BYOK might not be available
    }
  };

  useEffect(() => {
    if (user) {
      loadKeys();
      loadAIConfig();
      loadGitHub();
      fetchBilling().then(setBilling).catch(() => {});
      // Load AI plan toggle from localStorage
      setUseAiPlan(localStorage.getItem("awt_use_ai_plan") === "true");
    }
  }, [user]);

  const handleToggleAiPlan = (checked: boolean) => {
    setUseAiPlan(checked);
    localStorage.setItem("awt_use_ai_plan", checked ? "true" : "false");
  };

  const handleCreate = async () => {
    if (!newKeyName.trim()) return;
    setLoading(true);
    setError("");
    try {
      const created = await createApiKey(newKeyName.trim());
      setCreatedKey(created);
      setNewKeyName("");
      await loadKeys();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create key");
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async (key: string) => {
    await navigator.clipboard.writeText(key);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRevoke = async (id: number) => {
    if (!confirm(t("revokeConfirm"))) return;
    try {
      await deleteApiKey(id);
      await loadKeys();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to revoke key");
    }
  };

  // GitHub handlers
  const parseRepo = (val: string) => {
    const parts = val.split("/");
    return parts.length >= 2 ? { owner: parts[0], repo: parts.slice(1).join("/") } : null;
  };

  const handleVerifyGitHub = async () => {
    const parsed = parseRepo(ghRepo);
    if (!parsed) return;
    // If no new PAT entered and no saved connection, cannot verify
    if (!ghPat.trim() && !ghConn?.connected) return;
    setGhVerifying(true);
    setGhVerifyResult(null);
    setGhError("");
    try {
      // Send empty string when PAT unchanged — backend uses stored PAT
      const patToSend = ghPat.trim();
      const result = await verifyGitHubConnection(patToSend, parsed.owner, parsed.repo, ghBranch);
      setGhVerifyResult(result);
    } catch (err) {
      setGhError(err instanceof Error ? err.message : "Verify failed");
    } finally {
      setGhVerifying(false);
    }
  };

  const handleSaveGitHub = async () => {
    const parsed = parseRepo(ghRepo);
    if (!parsed) return;
    // New connection requires PAT; existing connection can save without it
    if (!ghPat.trim() && !ghConn?.connected) return;
    setGhSaving(true);
    setGhError("");
    setGhMessage("");
    try {
      // Send empty string when PAT unchanged — backend keeps stored PAT
      const conn = await saveGitHubConnection(ghPat.trim(), parsed.owner, parsed.repo, ghBranch);
      setGhConn(conn);
      setGhPat("");
      setGhMessage(t("githubSaved"));
      setTimeout(() => setGhMessage(""), 3000);
    } catch (err) {
      setGhError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setGhSaving(false);
    }
  };

  const handleRemoveGitHub = async () => {
    if (!confirm(t("removeGithubConfirm"))) return;
    setGhError("");
    setGhMessage("");
    try {
      await deleteGitHubConnection();
      setGhConn({ connected: false, owner: "", repo: "", default_branch: "main", pat_prefix: "", updated_at: null });
      setGhPat("");
      setGhRepo("");
      setGhBranch("main");
      setGhVerifyResult(null);
      setGhMessage(t("githubRemoved"));
      setTimeout(() => setGhMessage(""), 3000);
    } catch (err) {
      setGhError(err instanceof Error ? err.message : "Remove failed");
    }
  };

  // AI Config handlers
  const handleTestConnection = async () => {
    if (!aiApiKey.trim() && aiProvider !== "ollama") return;
    setAiTesting(true);
    setAiTestResult(null);
    setAiError("");
    try {
      const result = await testAIConfig(aiProvider, aiApiKey, aiModel);
      setAiTestResult(result);
    } catch (err) {
      setAiError(err instanceof Error ? err.message : "Test failed");
    } finally {
      setAiTesting(false);
    }
  };

  const handleSaveAIConfig = async () => {
    if (!aiApiKey.trim() && aiProvider !== "ollama") return;
    setAiSaving(true);
    setAiError("");
    setAiMessage("");
    try {
      const cfg = await saveAIConfig(aiProvider, aiApiKey, aiModel);
      setAiConfig(cfg);
      setAiApiKey("");
      setAiMessage(t("configSaved"));
      setTimeout(() => setAiMessage(""), 3000);
    } catch (err) {
      setAiError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setAiSaving(false);
    }
  };

  const handleRemoveAIConfig = async () => {
    if (!confirm(t("removeConfirm"))) return;
    setAiError("");
    setAiMessage("");
    try {
      await deleteAIConfig();
      setAiConfig({ provider: "", model: "", has_key: false, key_prefix: "", updated_at: null });
      setAiProvider("openai");
      setAiModel("");
      setAiApiKey("");
      setAiTestResult(null);
      setAiMessage(t("configRemoved"));
      setTimeout(() => setAiMessage(""), 3000);
    } catch (err) {
      setAiError(err instanceof Error ? err.message : "Remove failed");
    }
  };

  if (!user) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-8">
        <p className="text-gray-500">{t("loginRequired")}</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-8">
      <h1 className="mb-2 text-2xl font-bold text-gray-900">{t("title")}</h1>
      <p className="mb-8 text-sm text-gray-500">{t("subtitle")}</p>

      {/* GitHub Connection Section */}
      <div className="mb-6 rounded-lg border border-gray-200 bg-white p-6">
        <h2 className="mb-1 text-lg font-semibold text-gray-900">
          {t("githubTitle")}
        </h2>
        <p className="mb-4 text-sm text-gray-500">{t("githubDesc")}</p>

        {/* Status */}
        {ghConn?.connected && (
          <div className="mb-4 rounded border border-blue-200 bg-blue-50 px-4 py-3">
            <p className="text-sm text-blue-800">
              {t("githubConnected", { repo: `${ghConn.owner}/${ghConn.repo}` })}
            </p>
            {ghConn.updated_at && (
              <p className="mt-1 text-xs text-blue-600">
                {t("lastUpdated")}: {new Date(ghConn.updated_at).toLocaleDateString()}
              </p>
            )}
          </div>
        )}

        {!ghConn?.connected && (
          <div className="mb-4 rounded border border-amber-200 bg-amber-50 px-4 py-3">
            <p className="text-sm text-amber-800">{t("githubDisconnected")}</p>
          </div>
        )}

        {/* PAT */}
        <div className="mb-3">
          <label className="mb-1 block text-sm font-medium text-gray-700">
            {t("pat")}
          </label>
          <div className="relative">
            <input
              type={showPat ? "text" : "password"}
              value={ghPat}
              onChange={(e) => setGhPat(e.target.value)}
              placeholder={ghConn?.connected ? ghConn.pat_prefix : t("patPlaceholder")}
              className="w-full rounded border border-gray-300 px-3 py-2 pr-10 text-sm focus:border-blue-500 focus:outline-none"
            />
            <button
              type="button"
              onClick={() => setShowPat(!showPat)}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              {showPat ? (
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L6.59 6.59m7.532 7.532l3.29 3.29M3 3l18 18" /></svg>
              ) : (
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
              )}
            </button>
          </div>
          {ghConn?.connected && !ghPat.trim() && (
            <p className="mt-1 text-xs text-gray-400">{t("patKeptHint")}</p>
          )}
        </div>

        {/* Repository */}
        <div className="mb-3">
          <label className="mb-1 block text-sm font-medium text-gray-700">
            {t("repository")}
          </label>
          <input
            type="text"
            value={ghRepo}
            onChange={(e) => setGhRepo(e.target.value)}
            placeholder={t("repoPlaceholder")}
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          />
        </div>

        {/* Default Branch */}
        <div className="mb-4">
          <label className="mb-1 block text-sm font-medium text-gray-700">
            {t("defaultBranch")}
          </label>
          <input
            type="text"
            value={ghBranch}
            onChange={(e) => setGhBranch(e.target.value)}
            placeholder="main"
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          />
        </div>

        {/* Messages */}
        {ghError && (
          <div className="mb-3 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {ghError}
          </div>
        )}
        {ghMessage && (
          <div className="mb-3 rounded border border-green-200 bg-green-50 p-3 text-sm text-green-700">
            {ghMessage}
          </div>
        )}
        {ghVerifyResult && (
          <div className={`mb-3 rounded border p-3 text-sm ${ghVerifyResult.success ? "border-green-200 bg-green-50 text-green-700" : "border-red-200 bg-red-50 text-red-700"}`}>
            {ghVerifyResult.message}
          </div>
        )}

        {/* Buttons */}
        <div className="flex flex-wrap gap-2">
          <button
            onClick={handleVerifyGitHub}
            disabled={ghVerifying || !ghRepo.includes("/")}
            className="rounded border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            {ghVerifying ? t("verifyingConnection") : t("verifyConnection")}
          </button>
          <button
            onClick={handleSaveGitHub}
            disabled={ghSaving || (!ghPat.trim() && !ghConn?.connected) || !ghRepo.includes("/")}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {ghSaving ? t("savingGithub") : t("saveGithub")}
          </button>
          {ghConn?.connected && (
            <button
              onClick={handleRemoveGitHub}
              className="rounded px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50"
            >
              {t("removeGithub")}
            </button>
          )}
        </div>
      </div>

      {/* AI Provider Config Section */}
      <div className="mb-6 rounded-lg border border-gray-200 bg-white p-6">
        <h2 className="mb-1 text-lg font-semibold text-gray-900">
          {t("aiConfigTitle")}
        </h2>
        <p className="mb-4 text-sm text-gray-500">{t("aiConfigDesc")}</p>

        {/* Current status */}
        {aiConfig?.has_key && (
          <div className="mb-4 rounded border border-blue-200 bg-blue-50 px-4 py-3">
            <p className="text-sm text-blue-800">
              {t("usingOwnKey", { provider: aiConfig.provider.toUpperCase(), prefix: aiConfig.key_prefix })}
            </p>
            {aiConfig.updated_at && (
              <p className="mt-1 text-xs text-blue-600">
                {t("lastUpdated")}: {new Date(aiConfig.updated_at).toLocaleDateString()}
              </p>
            )}
          </div>
        )}

        {!aiConfig?.has_key && (
          <div className="mb-4 rounded border border-amber-200 bg-amber-50 px-4 py-3">
            <p className="text-sm text-amber-800">{t("noKeyWarning")}</p>
          </div>
        )}

        {/* Provider */}
        <div className="mb-3">
          <label className="mb-1 block text-sm font-medium text-gray-700">
            {t("provider")}
          </label>
          <select
            value={aiProvider}
            onChange={(e) => setAiProvider(e.target.value)}
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          >
            <option value="openai">OpenAI</option>
            <option value="anthropic">Anthropic</option>
            <option value="ollama">Ollama (Local)</option>
          </select>
        </div>

        {/* API Key */}
        {aiProvider !== "ollama" && (
          <div className="mb-3">
            <label className="mb-1 block text-sm font-medium text-gray-700">
              {t("apiKeyLabel")}
            </label>
            <div className="relative">
              <input
                type={showKey ? "text" : "password"}
                value={aiApiKey}
                onChange={(e) => setAiApiKey(e.target.value)}
                placeholder={aiConfig?.has_key ? aiConfig.key_prefix : t("apiKeyPlaceholder")}
                className="w-full rounded border border-gray-300 px-3 py-2 pr-10 text-sm focus:border-blue-500 focus:outline-none"
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                {showKey ? (
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L6.59 6.59m7.532 7.532l3.29 3.29M3 3l18 18" /></svg>
                ) : (
                  <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
                )}
              </button>
            </div>
          </div>
        )}

        {/* Model */}
        <div className="mb-4">
          <label className="mb-1 block text-sm font-medium text-gray-700">
            {t("model")}
          </label>
          <input
            type="text"
            value={aiModel}
            onChange={(e) => setAiModel(e.target.value)}
            placeholder={t("modelPlaceholder")}
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          />
        </div>

        {/* Messages */}
        {aiError && (
          <div className="mb-3 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {aiError}
          </div>
        )}
        {aiMessage && (
          <div className="mb-3 rounded border border-green-200 bg-green-50 p-3 text-sm text-green-700">
            {aiMessage}
          </div>
        )}
        {aiTestResult && (
          <div className={`mb-3 rounded border p-3 text-sm ${aiTestResult.success ? "border-green-200 bg-green-50 text-green-700" : "border-red-200 bg-red-50 text-red-700"}`}>
            {aiTestResult.message}
          </div>
        )}

        {/* Buttons */}
        <div className="flex flex-wrap gap-2">
          <button
            onClick={handleTestConnection}
            disabled={aiTesting || (!aiApiKey.trim() && aiProvider !== "ollama")}
            className="rounded border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            {aiTesting ? t("testingConnection") : t("testConnection")}
          </button>
          <button
            onClick={handleSaveAIConfig}
            disabled={aiSaving || (!aiApiKey.trim() && aiProvider !== "ollama")}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {aiSaving ? t("savingConfig") : t("saveConfig")}
          </button>
          {aiConfig?.has_key && (
            <button
              onClick={handleRemoveAIConfig}
              className="rounded px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50"
            >
              {t("removeConfig")}
            </button>
          )}
        </div>
      </div>

      {/* Advanced Options Section */}
      <div className="mb-6 rounded-lg border border-gray-200 bg-white p-6">
        <h2 className="mb-1 text-lg font-semibold text-gray-900">
          {t("advancedTitle")}
        </h2>
        <p className="mb-4 text-sm text-gray-500">{t("advancedDesc")}</p>

        <div className="flex items-center justify-between">
          <div className="flex-1">
            <p className="text-sm font-medium text-gray-700">{t("useAiPlan")}</p>
            <p className="text-xs text-gray-500">{t("useAiPlanDesc")}</p>
          </div>
          <button
            role="switch"
            aria-checked={useAiPlan}
            onClick={() => handleToggleAiPlan(!useAiPlan)}
            className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ${useAiPlan ? "bg-blue-600" : "bg-gray-200"}`}
          >
            <span
              className={`pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow ring-0 transition-transform duration-200 ${useAiPlan ? "translate-x-5" : "translate-x-0"}`}
            />
          </button>
        </div>
        <p className={`mt-2 text-xs ${useAiPlan ? "text-blue-600" : "text-gray-400"}`}>
          {useAiPlan ? t("enabled") : t("disabled")}
        </p>
      </div>

      {/* API Keys Section */}
      <div className="rounded-lg border border-gray-200 bg-white p-6">
        <h2 className="mb-1 text-lg font-semibold text-gray-900">
          {t("apiKeysTitle")}
        </h2>
        <p className="mb-4 text-sm text-gray-500">{t("apiKeysDesc")}</p>

        {billing?.tier === "free" ? (
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-center">
            <p className="mb-3 text-sm text-amber-800">{t("apiKeysProOnly")}</p>
            <Link
              href="/pricing"
              className="inline-block rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              {t("upgradeToPro")}
            </Link>
          </div>
        ) : (
        <>
        {/* Create new key */}
        <div className="mb-4 flex gap-2">
          <input
            type="text"
            value={newKeyName}
            onChange={(e) => setNewKeyName(e.target.value)}
            placeholder={t("keyNamePlaceholder")}
            className="flex-1 rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            onKeyDown={(e) => e.key === "Enter" && handleCreate()}
          />
          <button
            onClick={handleCreate}
            disabled={loading || !newKeyName.trim()}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? t("generating") : t("generate")}
          </button>
        </div>

        {error && (
          <div className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Newly created key (show once) */}
        {createdKey && (
          <div className="mb-4 rounded border border-green-200 bg-green-50 p-4">
            <p className="mb-2 text-sm font-medium text-green-800">
              {t("keyCreated")}
            </p>
            <div className="flex items-center gap-2">
              <code className="flex-1 rounded bg-white px-3 py-2 font-mono text-sm text-gray-900 border border-green-200">
                {createdKey.key}
              </code>
              <button
                onClick={() => handleCopy(createdKey.key)}
                className="rounded bg-green-600 px-3 py-2 text-sm text-white hover:bg-green-700"
              >
                {copied ? t("copied") : t("copy")}
              </button>
            </div>
            <p className="mt-2 text-xs text-green-700">{t("keyWarning")}</p>
          </div>
        )}

        {/* Key list */}
        {keys.length === 0 ? (
          <p className="py-4 text-center text-sm text-gray-400">
            {t("noKeys")}
          </p>
        ) : (
          <div className="space-y-2">
            {keys.map((k) => (
              <div
                key={k.id}
                className="flex items-center justify-between rounded border border-gray-200 px-4 py-3"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <code className="font-mono text-sm text-gray-600">
                      {k.prefix}...
                    </code>
                    <span className="text-sm text-gray-800">{k.name}</span>
                  </div>
                  <div className="mt-1 text-xs text-gray-400">
                    {t("created")}{" "}
                    {new Date(k.created_at).toLocaleDateString()}
                    {k.last_used_at && (
                      <>
                        {" · "}
                        {t("lastUsed")}{" "}
                        {new Date(k.last_used_at).toLocaleDateString()}
                      </>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => handleRevoke(k.id)}
                  className="rounded px-3 py-1 text-sm text-red-600 hover:bg-red-50"
                >
                  {t("revoke")}
                </button>
              </div>
            ))}
          </div>
        )}
        </>
        )}
      </div>
    </div>
  );
}
