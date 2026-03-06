"use client";

import { useTranslations } from "next-intl";

interface Props {
  currentStep: number;
  completedSteps: number[];
}

export default function StepIndicator({ currentStep, completedSteps }: Props) {
  const t = useTranslations("steps");

  const steps = [
    { num: 1, label: t("step1") },
    { num: 2, label: t("step2") },
    { num: 3, label: t("step3") },
    { num: 4, label: t("step4") },
    { num: 5, label: t("step5") },
  ];

  const isCompleted = (num: number) => completedSteps.includes(num);
  const isCurrent = (num: number) => num === currentStep;
  const isLineGreen = (index: number) => isCompleted(steps[index].num);

  return (
    <div className="w-full">
      <div className="flex items-center">
        {steps.map((step, index) => (
          <div key={step.num} className="flex flex-1 flex-col items-center relative">
            <div className="flex w-full items-center">
              {/* Left connector */}
              {index > 0 && (
                <div
                  className={`h-0.5 flex-1 ${
                    isLineGreen(index - 1) ? "bg-green-500" : "bg-gray-200"
                  }`}
                />
              )}

              {/* Circle */}
              <div
                className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                  isCompleted(step.num)
                    ? "bg-green-500 text-white"
                    : isCurrent(step.num)
                    ? "bg-blue-600 text-white"
                    : "border-2 border-gray-300 bg-white text-gray-400"
                }`}
              >
                {isCompleted(step.num) ? (
                  <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  step.num
                )}
              </div>

              {/* Right connector */}
              {index < steps.length - 1 && (
                <div
                  className={`h-0.5 flex-1 ${
                    isLineGreen(index) ? "bg-green-500" : "bg-gray-200"
                  }`}
                />
              )}
            </div>

            {/* Label */}
            <span
              className={`mt-1.5 hidden text-center text-[11px] leading-tight whitespace-nowrap sm:block ${
                isCompleted(step.num)
                  ? "font-medium text-green-600"
                  : isCurrent(step.num)
                  ? "font-bold text-blue-600"
                  : "text-gray-400"
              }`}
            >
              {step.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
