"use client";

import React, { useState } from "react";
import Link from "next/link";
import { StudentLayout } from "@/components/layout/StudentLayout";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import {
  Sparkles,
  ArrowRight,
  CheckCircle2,
  ExternalLink,
  Layers,
  ChevronLeft,
  Eye,
} from "lucide-react";

const STITCH_DESIGNS = [
  {
    id: "design-1",
    title: "Variant 1: Cozy Notion Student Desk",
    subtitle: "Warm slate-espresso charcoal, study streak flame, ambient widget & vertical timeline",
    image: "/stitch/design1-cozy-notion.png",
    palette: ["#191816 (Warm Charcoal)", "#EAB308 (Amber Flame)", "#FEF3C7 (Warm Parchment)", "#9EC899 (Sage Green)"],
    features: [
      "Top cover banner with floating emoji avatar (✨ 📚 ☕)",
      "Big visual study streak counter with daily focus goal",
      "Interactive vertical class schedule timeline with safe-bunk margin tracker",
      "Resume Studying shelf (one click to resume DBMS Unit 3, slide 42)",
      "Notion callouts with lightbulb reminders",
    ],
    vibe: "Warm, personal, calm, and aesthetic — feels like your own physical study desk.",
  },
  {
    id: "design-2",
    title: "Variant 2: Academic Monolith (Notion Baseline)",
    subtitle: "Editorial knowledge system with 3 Notion Gallery cards and soft pastel tags",
    image: "/stitch/design2-academic-monolith.png",
    palette: ["#191919 (Canvas)", "#222222 (Containers)", "#B4A0E5 (Lavender)", "#8FBCE6 (Muted Sky)"],
    features: [
      "3 Notion Gallery Cards with cover strips (Study Corner, Routine, Career)",
      "High-legibility typography (Newsreader serif + Inter sans)",
      "Executive summary callout boxes for tonight's assignment deadlines",
      "Quick status badges for ESE exam countdown (8 days)",
      "Minimalist hairline borders (#333333) with zero optical glare",
    ],
    vibe: "Austere, intellectual, structured, and distraction-free.",
  },
  {
    id: "design-3",
    title: "Variant 3: Editorial Bento & Study Vault",
    subtitle: "Pitch-black architectural bento grid with high-speed study vault launcher",
    image: "/stitch/design3-editorial-bento.png",
    palette: ["#0A0A0A (Pitch Black)", "#121212 (Bento Tiles)", "#10B981 (Emerald Accent)", "#27272A (Hairline)"],
    features: [
      "Architectural Bento Grid layout with spacious modular cards",
      "Quick Study Vault Launcher (one-click access to Syllabus, PYQs, Notes)",
      "Active module progress with LeetCode tracker (142/200)",
      "Compact schedule with immediate attendance risk matrix",
      "Git commit launcher for assignments",
    ],
    vibe: "Hyper-clean, razor-sharp, modern engineer aesthetic.",
  },
];

export default function DesignShowcasePage() {
  const [selectedDesign, setSelectedDesign] = useState(STITCH_DESIGNS[0]);
  const [fullScreenModal, setFullScreenModal] = useState(false);

  return (
    <StudentLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-xl font-bold text-white tracking-tight">
                Stitch UI Design Comparison
              </h1>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-indigo-500/15 text-indigo-300 border border-indigo-500/30 font-semibold flex items-center gap-1">
                <Sparkles className="w-3.5 h-3.5 text-[#5E6AD2]" />
                Google Stitch MCP
              </span>
            </div>
            <p className="text-xs text-[#8A8F98] mt-0.5">
              Compare the 3 AI-generated Stitch designs for the student portal · Click a design to inspect
            </p>
          </div>

          <Link href="/">
            <Button size="md" variant="secondary" icon={<ChevronLeft className="w-3.5 h-3.5" />}>
              Back to Home
            </Button>
          </Link>
        </div>

        {/* 3-Tab Selector Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {STITCH_DESIGNS.map((d) => {
            const isSelected = selectedDesign.id === d.id;

            return (
              <Card
                key={d.id}
                onClick={() => setSelectedDesign(d)}
                className={`p-4 cursor-pointer transition-all space-y-2.5 ${
                  isSelected
                    ? "border-[#5E6AD2] bg-[#121316] shadow-lg shadow-indigo-500/10"
                    : "border-white/[0.08] hover:border-white/[0.16] bg-[#0D0E10]"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span
                    className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded ${
                      isSelected
                        ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/40"
                        : "bg-white/[0.04] text-[#8A8F98]"
                    }`}
                  >
                    {d.id.toUpperCase()}
                  </span>
                  {isSelected && (
                    <span className="text-xs text-emerald-400 flex items-center gap-1 font-medium">
                      <CheckCircle2 className="w-3.5 h-3.5" /> Selected
                    </span>
                  )}
                </div>

                <div>
                  <h3 className="text-sm font-bold text-white">{d.title}</h3>
                  <p className="text-[11px] text-[#8A8F98] line-clamp-2 mt-0.5">{d.subtitle}</p>
                </div>

                <div className="w-full h-24 rounded-md overflow-hidden border border-white/[0.08] relative group">
                  <img
                    src={d.image}
                    alt={d.title}
                    className="w-full h-full object-cover object-top opacity-80 group-hover:opacity-100 transition-opacity"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent flex items-end p-2">
                    <span className="text-[10px] font-mono text-white flex items-center gap-1">
                      <Eye className="w-3 h-3 text-[#5E6AD2]" /> Click to inspect
                    </span>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>

        {/* Deep Inspection Panel */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left: Full High-Res Preview (8 Cols) */}
          <div className="lg:col-span-8 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-[#8A8F98] flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-[#5E6AD2]" /> Full Screen Render
              </span>
              <button
                onClick={() => setFullScreenModal(true)}
                className="text-xs text-[#5E6AD2] hover:underline flex items-center gap-1"
              >
                Open Fullscreen <ExternalLink className="w-3 h-3" />
              </button>
            </div>

            <Card className="p-3 bg-[#0D0E10] border-white/[0.08] overflow-hidden">
              <div className="max-h-[650px] overflow-y-auto rounded-lg border border-white/[0.08]">
                <img
                  src={selectedDesign.image}
                  alt={selectedDesign.title}
                  className="w-full h-auto object-contain cursor-zoom-in"
                  onClick={() => setFullScreenModal(true)}
                />
              </div>
            </Card>
          </div>

          {/* Right: Design Spec & Features (4 Cols) */}
          <div className="lg:col-span-4 space-y-4">
            <Card className="p-5 bg-[#0D0E10] border-white/[0.08] space-y-4">
              <div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/15 text-indigo-300 border border-indigo-500/30">
                  Design Specifications
                </span>
                <h2 className="text-base font-bold text-white mt-2">{selectedDesign.title}</h2>
                <p className="text-xs text-[#8A8F98] mt-1 leading-relaxed">{selectedDesign.vibe}</p>
              </div>

              {/* Color Palette */}
              <div className="space-y-2 pt-2 border-t border-white/[0.06]">
                <span className="text-[11px] font-semibold text-[#8A8F98] uppercase tracking-wider block">
                  Tonal Palette:
                </span>
                <div className="space-y-1.5">
                  {selectedDesign.palette.map((c, idx) => (
                    <div
                      key={idx}
                      className="text-xs font-mono p-2 rounded bg-[#121316] border border-white/[0.04] text-[#ECEEF0]"
                    >
                      {c}
                    </div>
                  ))}
                </div>
              </div>

              {/* Key Features */}
              <div className="space-y-2 pt-2 border-t border-white/[0.06]">
                <span className="text-[11px] font-semibold text-[#8A8F98] uppercase tracking-wider block">
                  Key UI Architecture:
                </span>
                <div className="space-y-2">
                  {selectedDesign.features.map((feat, fIdx) => (
                    <div key={fIdx} className="flex items-start gap-2 text-xs text-[#ECEEF0] leading-snug">
                      <span className="w-1.5 h-1.5 rounded-full bg-[#5E6AD2] shrink-0 mt-1.5" />
                      <span>{feat}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Action Button */}
              <div className="pt-3 border-t border-white/[0.06]">
                <Button
                  size="md"
                  variant="primary"
                  className="w-full"
                  icon={<ArrowRight className="w-4 h-4" />}
                >
                  Apply This Design to Portal
                </Button>
              </div>
            </Card>
          </div>
        </div>

        {/* Fullscreen Modal */}
        {fullScreenModal && (
          <div
            className="fixed inset-0 z-50 bg-black/90 backdrop-blur-md flex flex-col p-4 overflow-hidden"
            onClick={() => setFullScreenModal(false)}
          >
            <div className="flex items-center justify-between pb-3 px-2">
              <span className="text-sm font-bold text-white">{selectedDesign.title}</span>
              <button
                onClick={() => setFullScreenModal(false)}
                className="text-xs text-[#8A8F98] hover:text-white px-3 py-1 rounded bg-white/[0.1]"
              >
                Close (ESC)
              </button>
            </div>
            <div className="flex-1 overflow-auto rounded-lg border border-white/[0.1] bg-[#121316] p-2 flex justify-center">
              <img
                src={selectedDesign.image}
                alt={selectedDesign.title}
                className="max-w-full h-auto object-contain"
              />
            </div>
          </div>
        )}
      </div>
    </StudentLayout>
  );
}

