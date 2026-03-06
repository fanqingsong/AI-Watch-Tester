"use client";

import { useState, useMemo } from "react";
import { useTranslations } from "next-intl";
import yaml from "js-yaml";
import { updateScenarios, approveTest } from "@/lib/api";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

interface ScenarioStep {
  step: number;
  action: string;
  description?: string;
  value?: string;
  target?: { text?: string };
  assert_type?: string;
  expected?: Array<{ type?: string; value?: string }>;
}

interface ParsedScenario {
  id: string;
  name: string;
  description?: string;
  tags?: string[];
  steps: ScenarioStep[];
  expected_result?: Array<{ type?: string; value?: string } | string>;
}

interface Props {
  testId: number;
  initialYaml: string;
  onApprove: () => void;
}

/* ------------------------------------------------------------------ */
/* Step → icon + human-readable text                                  */
/* ------------------------------------------------------------------ */

function describeStep(step: ScenarioStep): { icon: string; text: string } {
  switch (step.action) {
    case "navigate":
      return {
        icon: "\u{1F310}",
        text: `Navigate to ${step.value || "..."}`,
      };

    case "find_and_click":
      return {
        icon: "\u{1F446}",
        text: `Click '${step.target?.text || step.value || "element"}'`,
      };

    case "find_and_type":
      return {
        icon: "\u2328\uFE0F",
        text: `Type '${step.value || "..."}' in '${step.target?.text || "field"}'`,
      };

    case "assert": {
      const exp = step.expected?.[0];
      const assertValue = exp?.value || step.value || "...";
      return {
        icon: "\u2705",
        text: `Verify: ${step.description || assertValue}`,
      };
    }

    case "wait": {
      const ms = parseInt(step.value || "1000", 10);
      const seconds = (ms / 1000).toFixed(ms % 1000 === 0 ? 0 : 1);
      return { icon: "\u23F3", text: `Wait ${seconds}s` };
    }

    case "screenshot":
      return { icon: "\u{1F4F8}", text: "Capture screenshot" };

    default:
      return {
        icon: "\u25B6\uFE0F",
        text: step.description || step.action,
      };
  }
}

/* ------------------------------------------------------------------ */
/* Sub-components                                                      */
/* ------------------------------------------------------------------ */

function SourceBadge({ isPattern, t }: { isPattern: boolean; t: (k: string) => string }) {
  if (isPattern) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700">
        <span>{"⚙️"}</span>
        {t("patternBadge")}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-purple-100 px-2 py-0.5 text-xs font-medium text-purple-700">
      <span>{"🤖"}</span>
      {t("aiBadge")}
    </span>
  );
}

function ScenarioCard({
  scenario,
  onDelete,
  t,
}: {
  scenario: ParsedScenario;
  onDelete: () => void;
  t: (k: string, v?: Record<string, string>) => string;
}) {
  const [expanded, setExpanded] = useState(false);
  const isPattern = scenario.tags?.includes("pattern-generated") ?? false;
  const stepCount = scenario.steps?.length || 0;

  const handleDelete = () => {
    if (window.confirm(t("deleteConfirm"))) {
      onDelete();
    }
  };

  return (
    <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
      {/* Card header */}
      <div className="border-b border-gray-100 px-4 py-3">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-sm font-semibold text-gray-900">
                {scenario.id && (
                  <span className="mr-1.5 text-gray-400">{scenario.id}</span>
                )}
                {scenario.name}
              </h3>
              <SourceBadge isPattern={isPattern} t={t} />
              <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500">
                {t("stepsCount", { count: String(stepCount) })}
              </span>
            </div>
            {scenario.description && (
              <p className="mt-0.5 text-xs text-gray-500">{scenario.description}</p>
            )}
          </div>

          {/* Delete button */}
          <button
            onClick={handleDelete}
            className="shrink-0 p-1 text-gray-400 transition-colors hover:text-red-500"
            title={t("delete")}
            aria-label={t("delete")}
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
              />
            </svg>
          </button>
        </div>

        {/* Tags */}
        {scenario.tags && scenario.tags.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {scenario.tags.map((tag, ti) => (
              <span
                key={ti}
                className="rounded-full bg-indigo-50 px-2 py-0.5 text-[11px] font-medium text-indigo-600"
              >
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Expand/collapse toggle */}
      <div className="px-4 py-2">
        <button
          onClick={() => setExpanded((v) => !v)}
          className="text-xs font-medium text-gray-400 hover:text-gray-600"
        >
          {expanded ? t("collapse") : t("expand")}
        </button>
      </div>

      {/* Steps (expanded) */}
      {expanded && (
        <>
          <div className="divide-y divide-gray-50 px-4">
            {scenario.steps?.map((step, i) => {
              const { icon, text } = describeStep(step);
              return (
                <div key={i} className="flex items-start gap-3 py-2.5">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-50 text-xs font-semibold text-blue-600">
                    {step.step}
                  </span>
                  <div className="min-w-0 pt-0.5">
                    <p className="text-sm text-gray-700">
                      <span className="mr-1.5">{icon}</span>
                      {text}
                    </p>
                    {step.description &&
                      step.action !== "navigate" &&
                      step.action !== "screenshot" && (
                        <p className="mt-0.5 text-xs text-gray-400">{step.description}</p>
                      )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Expected results */}
          {scenario.expected_result && scenario.expected_result.length > 0 && (
            <div className="border-t border-gray-100 bg-green-50/50 px-4 py-2.5">
              <p className="text-xs font-medium text-green-700">Expected Results</p>
              <ul className="mt-1 space-y-0.5">
                {scenario.expected_result.map((er, ei) => (
                  <li key={ei} className="text-xs text-green-600">
                    {"\u2705"}{" "}
                    {typeof er === "string" ? er : er.value || JSON.stringify(er)}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Main component                                                      */
/* ------------------------------------------------------------------ */

export default function ScenarioReview({ testId, initialYaml, onApprove }: Props) {
  const t = useTranslations("scenarioReview");

  const [currentYaml, setCurrentYaml] = useState(initialYaml);
  const [showEditor, setShowEditor] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [approving, setApproving] = useState(false);
  const [error, setError] = useState("");

  // YAML 파싱: 배열 또는 단일 오브젝트 모두 처리
  const scenarios: ParsedScenario[] = useMemo(() => {
    try {
      const parsed = yaml.load(currentYaml);
      if (Array.isArray(parsed)) return parsed as ParsedScenario[];
      if (parsed && typeof parsed === "object") return [parsed as ParsedScenario];
      return [];
    } catch {
      return [];
    }
  }, [currentYaml]);

  // 시나리오 삭제 후 YAML 재생성
  const handleDelete = (index: number) => {
    const updated = scenarios.filter((_, i) => i !== index);
    try {
      const newYaml = updated.length > 0 ? yaml.dump(updated, { flowLevel: -1 }) : "";
      setCurrentYaml(newYaml);
      setSaved(false);
    } catch {
      setError("Failed to update YAML after deletion");
    }
  };

  const handleSave = async () => {
    setError("");
    setSaving(true);
    setSaved(false);
    try {
      await updateScenarios(testId, currentYaml);
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  const handleRunTest = async () => {
    setError("");
    setApproving(true);
    try {
      await updateScenarios(testId, currentYaml);
      await approveTest(testId);
      onApprove();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to approve");
    } finally {
      setApproving(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-medium text-gray-700">{t("title")}</h3>
          {scenarios.length > 0 && (
            <p className="mt-0.5 text-xs text-gray-500">
              {t("scenarioCount", { count: String(scenarios.length) })}
            </p>
          )}
        </div>
        <button
          onClick={() => setShowEditor((v) => !v)}
          className={`rounded-lg border px-3 py-1 text-xs font-medium transition-colors ${
            showEditor
              ? "border-gray-400 bg-gray-100 text-gray-700"
              : "border-gray-200 text-gray-500 hover:bg-gray-50"
          }`}
        >
          {showEditor ? t("visualView") : t("editYaml")}
        </button>
      </div>

      {/* YAML editor (advanced, hidden by default) */}
      {showEditor && (
        <div className="space-y-3">
          <textarea
            value={currentYaml}
            onChange={(e) => {
              setCurrentYaml(e.target.value);
              setSaved(false);
            }}
            className="w-full rounded-lg border border-gray-300 bg-gray-50 p-3 font-mono text-xs leading-relaxed text-gray-800 focus:border-blue-500 focus:outline-none"
            rows={16}
            spellCheck={false}
          />
          <button
            onClick={handleSave}
            disabled={saving}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            {saving ? t("saving") : saved ? t("saved") : t("save")}
          </button>
        </div>
      )}

      {/* Visual card view (default) */}
      {!showEditor && (
        <>
          {scenarios.length === 0 ? (
            <div className="rounded-xl border border-dashed border-gray-200 bg-gray-50 px-6 py-10 text-center">
              <p className="text-sm text-gray-500">{t("noScenarios")}</p>
            </div>
          ) : (
            <div className="space-y-3">
              {scenarios.map((scenario, i) => (
                <ScenarioCard
                  key={`${scenario.id ?? i}-${i}`}
                  scenario={scenario}
                  onDelete={() => handleDelete(i)}
                  t={t}
                />
              ))}
            </div>
          )}
        </>
      )}

      {/* Error message */}
      {error && (
        <div className="rounded-lg bg-red-50 p-2 text-xs text-red-600">{error}</div>
      )}

      {/* Run Test button */}
      <button
        onClick={handleRunTest}
        disabled={approving || scenarios.length === 0}
        className="w-full rounded-lg bg-green-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
      >
        {approving ? t("starting") : t("runTest")}
      </button>
    </div>
  );
}
