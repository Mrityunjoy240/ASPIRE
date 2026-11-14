"use client";

import React, { useEffect, useState } from "react";
import { WebLayout } from "@/components/layout/WebLayout";
import { fetchInstitutions, updateInstitutionRules } from "@/lib/api";
import { Institution, InstitutionRules } from "@/lib/types";

export default function InstitutionAdminPage() {
  const [institutions, setInstitutions] = useState<Institution[]>([]);
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const data = await fetchInstitutions();
        setInstitutions(data);
      } catch (e) {
        console.error("Failed to load institutions", e);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  async function handleRuleChange(instId: string, field: keyof InstitutionRules, value: InstitutionRules[keyof InstitutionRules]) {
    setSavingId(instId);
    try {
      await updateInstitutionRules(instId, { [field]: value });
      // Optimistic update locally
      setInstitutions((prev) =>
        prev.map((inst) =>
          inst.id === instId
            ? { ...inst, rules: { ...(inst.rules ?? {}), [field]: value } as InstitutionRules }
            : inst
        )
      );
    } catch {
      alert("Failed to update institutional rule");
    } finally {
      setSavingId(null);
    }
  }

  if (loading) {
    return (
      <WebLayout>
        <div className="p-8 font-mono text-xs text-[#9DA3AE] flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#5E6AD2] linear-pulse-dot" />
          <span>Synchronizing multi-tenant institution rules...</span>
        </div>
      </WebLayout>
    );
  }

  return (
    <WebLayout>
      <div className="space-y-6 page-enter max-w-5xl mx-auto">
        {/* Header - Linear Style */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-5 border-b border-white/[0.08]">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2.5">
              <h1 className="text-xl font-bold tracking-tight text-[#FFFFFF]">
                Institution Control Plane
              </h1>
              <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded bg-white/[0.05] text-[#ECEEF0] border border-white/[0.10]">
                Multi-Tenant Governance
              </span>
            </div>
            <p className="text-[13px] text-[#9DA3AE]">
              Per-college deterministic thresholds, evaluation rules, and audit configurations
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button className="h-8 px-3 text-[13px] font-medium bg-white hover:bg-white/90 text-[#08090A] rounded-lg transition-all active:scale-[0.98] shadow-sm flex items-center">
              + Register Institution
            </button>
          </div>
        </div>

        {/* Institutions List */}
        <div className="space-y-4">
          {institutions.length === 0 ? (
            <div className="p-12 border border-dashed border-white/[0.08] rounded-xl text-center text-[#9DA3AE] font-mono text-sm">
              NO_INSTITUTIONS_REGISTERED
            </div>
          ) : (
            institutions.map((inst) => (
              <div
                key={inst.id}
                className="bg-[#121316] border border-white/[0.08] hover:border-white/[0.14] rounded-xl overflow-hidden transition-all duration-150 shadow-sm"
              >
                {/* Institution Identity Header */}
                <div className="px-4 py-3 border-b border-white/[0.08] bg-white/[0.02] flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 linear-pulse-dot" />
                    <h2 className="text-base font-semibold text-[#FFFFFF]">
                      {inst.name}
                      <span className="text-[#9DA3AE] font-mono ml-2 text-xs font-normal">
                        [{inst.slug}]
                      </span>
                    </h2>
                  </div>
                  <div className="flex items-center gap-3 text-xs">
                    <span className="text-xs font-mono px-2 py-0.5 rounded-md bg-white/[0.04] text-[#ECEEF0] border border-white/[0.08]">
                      Status: {inst.status}
                    </span>
                    {savingId === inst.id && (
                      <span className="text-xs font-mono text-[#A5AEF6] animate-pulse font-semibold">
                        SAVING...
                      </span>
                    )}
                  </div>
                </div>

                {/* Rules Management Grid */}
                <div className="p-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
                  {/* Attendance Threshold */}
                  <div className="space-y-2">
                    <label className="text-xs font-mono font-semibold text-[#9DA3AE] uppercase tracking-wider block">
                      Attendance Threshold
                    </label>
                    <div className="flex items-center gap-2">
                      <input
                        type="number"
                        value={inst.rules?.attendance_threshold ?? ""}
                        onChange={(e) =>
                          handleRuleChange(inst.id, "attendance_threshold", parseFloat(e.target.value))
                        }
                        className="bg-[#08090A] border border-white/[0.08] text-[#FFFFFF] font-mono text-sm px-2.5 h-8 rounded-md w-full focus:outline-none focus:border-white/[0.2] transition-colors"
                      />
                      <span className="text-[#9DA3AE] font-mono text-sm font-semibold">%</span>
                    </div>
                  </div>

                  {/* Grade Threshold */}
                  <div className="space-y-2">
                    <label className="text-xs font-mono font-semibold text-[#9DA3AE] uppercase tracking-wider block">
                      Grade Threshold
                    </label>
                    <div className="flex items-center gap-2">
                      <input
                        type="number"
                        value={inst.rules?.grade_threshold ?? ""}
                        onChange={(e) =>
                          handleRuleChange(inst.id, "grade_threshold", parseFloat(e.target.value))
                        }
                        className="bg-[#08090A] border border-white/[0.08] text-[#FFFFFF] font-mono text-sm px-2.5 h-8 rounded-md w-full focus:outline-none focus:border-white/[0.2] transition-colors"
                      />
                      <span className="text-[#9DA3AE] font-mono text-sm font-semibold">%</span>
                    </div>
                  </div>

                  {/* Escalation Period */}
                  <div className="space-y-2">
                    <label className="text-xs font-mono font-semibold text-[#9DA3AE] uppercase tracking-wider block">
                      Escalation Window
                    </label>
                    <div className="flex items-center gap-2">
                      <input
                        type="number"
                        value={inst.rules?.escalation_days ?? ""}
                        onChange={(e) =>
                          handleRuleChange(inst.id, "escalation_days", parseInt(e.target.value))
                        }
                        className="bg-[#08090A] border border-white/[0.08] text-[#FFFFFF] font-mono text-sm px-2.5 h-8 rounded-md w-full focus:outline-none focus:border-white/[0.2] transition-colors"
                      />
                      <span className="text-[#9DA3AE] font-mono text-sm">Days</span>
                    </div>
                  </div>

                  {/* AI Intelligence Toggle */}
                  <div className="space-y-2">
                    <label className="text-xs font-mono font-semibold text-[#9DA3AE] uppercase tracking-wider block">
                      Autonomous Intelligence
                    </label>
                    <button
                      onClick={() =>
                        handleRuleChange(inst.id, "ai_enabled", !(inst.rules?.ai_enabled ?? false))
                      }
                      className={`w-full h-8 px-2.5 rounded-md text-xs font-mono font-semibold transition-all border ${
                        inst.rules?.ai_enabled
                          ? "bg-[#5E6AD2]/15 border-[#5E6AD2]/40 text-[#A5AEF6]"
                          : "bg-[#08090A] border-white/[0.08] text-[#9DA3AE]"
                      }`}
                    >
                      {inst.rules?.ai_enabled ? "AGENT_DISPATCH_ON" : "AGENT_DISPATCH_OFF"}
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* System Footnote */}
        <div className="pt-4 border-t border-white/[0.08] flex items-center justify-between text-xs font-mono text-[#9DA3AE]">
          <span>ASPIRE Core Multi-Tenant Platform</span>
          <span>Last Audit Sync: Verified</span>
        </div>
      </div>
    </WebLayout>
  );
}
