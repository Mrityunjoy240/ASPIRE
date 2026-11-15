"use client";

import React, { useState } from "react";
import { MobileLayout } from "@/components/MobileLayout";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Priority } from "@aspire/shared";

const TASKS: Task[] = [
  {
    id: "1",
    title: "Submit Math Assignment 2",
    source: "Assessment",
    deadline: "Tomorrow 23:59",
    duration: "45 min",
    priority: "high",
    status: "pending" as const,
    sourceType: "ASSESSMENT",
  },
  {
    id: "2",
    title: "Review Module 3 Notes - Normalization",
    source: "AI Plan",
    deadline: "Today 22:00",
    duration: "60 min",
    priority: "high",
    status: "pending" as const,
    sourceType: "AI_PLAN",
  },
  {
    id: "3",
    title: "DBMS Recovery: Attend next 3 classes",
    source: "AI Plan",
    deadline: "This week",
    duration: "3 sessions",
    priority: "critical",
    status: "pending" as const,
    sourceType: "AI_PLAN",
  },
  {
    id: "4",
    title: "CN Lab Report - Week 2",
    source: "Calendar",
    deadline: "Friday 17:00",
    duration: "90 min",
    priority: "medium",
    status: "completed" as const,
    sourceType: "CALENDAR",
  },
  {
    id: "5",
    title: "Review Module 2 Quiz Results",
    source: "Assessment",
    deadline: "No deadline",
    duration: "30 min",
    priority: "low",
    status: "snoozed" as const,
    sourceType: "ASSESSMENT",
  },
];

type TaskStatus = "pending" | "completed" | "snoozed";

interface Task {
  id: string;
  title: string;
  source: string;
  deadline: string;
  duration: string;
  priority: Priority;
  status: TaskStatus;
  sourceType: string;
}

function getPriorityColor(priority: Priority) {
  switch (priority) {
    case "critical": return "text-rose-400 bg-rose-500/10 border-rose-500/30";
    case "high": return "text-amber-400 bg-amber-500/10 border-amber-500/30";
    case "medium": return "text-sky-400 bg-sky-500/10 border-sky-500/30";
    case "low": return "text-slate-400 bg-slate-500/10 border-slate-500/30";
  }
}

function getStatusLabel(status: TaskStatus) {
  switch (status) {
    case "pending": return "Pending";
    case "completed": return "Completed";
    case "snoozed": return "Snoozed";
  }
}

function getSourceIcon(sourceType: string) {
  switch (sourceType) {
    case "AI_PLAN":
      return (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-indigo-400">
          <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
        </svg>
      );
    case "ASSESSMENT":
      return (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-amber-400">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
        </svg>
      );
    case "CALENDAR":
      return (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-sky-400">
          <rect x="3" y="4" width="18" height="18" rx="2" />
          <line x1="16" y1="2" x2="16" y2="6" />
          <line x1="8" y1="2" x2="8" y2="6" />
          <line x1="3" y1="10" x2="21" y2="10" />
        </svg>
      );
    case "MENTOR":
      return (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-rose-400">
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
          <circle cx="9" cy="7" r="4" />
          <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
          <path d="M16 3.13a4 4 0 0 1 0 7.75" />
        </svg>
      );
    default:
      return (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-slate-400">
          <circle cx="12" cy="12" r="10" />
        </svg>
      );
  }
}

export default function TasksPage() {
  const [filter, setFilter] = useState<"all" | "pending" | "completed" | "snoozed">("all");

  const filteredTasks = TASKS.filter((task) => {
    if (filter === "all") return true;
    return task.status === filter;
  });

  const pendingCount = TASKS.filter((t) => t.status === "pending").length;
  const completedCount = TASKS.filter((t) => t.status === "completed").length;

  return (
    <MobileLayout>
      <div className="p-4 space-y-4 animate-slide-up">
        {/* Header */}
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-page-title">Tasks</h1>
            <p className="text-body">
              {pendingCount} pending · {completedCount} completed
            </p>
          </div>
        </header>

        {/* Filter Tabs */}
        <div className="flex gap-2 overflow-x-auto pb-2">
          {(["all", "pending", "completed", "snoozed"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-all duration-200 ${
                filter === f
                  ? "bg-indigo-500/20 text-indigo-400 border border-indigo-500/30"
                  : "bg-white/[0.03] text-slate-400 hover:text-slate-200"
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>

        {/* Task List */}
        <div className="space-y-3">
          {filteredTasks.map((task) => (
            <Card key={task.id} className={`group ${task.status === "completed" ? "opacity-70" : ""}`}>
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-start gap-3">
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center border ${
                      task.sourceType === "AI_PLAN" ? "bg-indigo-500/20 border-indigo-500/30 text-indigo-400"
                      : task.sourceType === "ASSESSMENT" ? "bg-amber-500/20 border-amber-500/30 text-amber-400"
                      : task.sourceType === "CALENDAR" ? "bg-sky-500/20 border-sky-500/30 text-sky-400"
                      : "bg-rose-500/20 border-rose-500/30 text-rose-400"
                    }`}>
                      {getSourceIcon(task.sourceType)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-semibold text-white truncate">{task.title}</h3>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-semibold font-mono border ${getPriorityColor(task.priority as Priority)}`}>
                          {task.priority.charAt(0).toUpperCase() + task.priority.slice(1)}
                        </span>
                      </div>
                      <p className="text-body text-slate-400 text-sm mb-2">{task.source}</p>
                      <div className="flex items-center gap-4 text-xs text-slate-500">
                        <span className="flex items-center gap-1">
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-slate-500">
                            <circle cx="12" cy="12" r="10" />
                            <polyline points="12 6 12 12 16 14" />
                          </svg>
                          {task.deadline}
                        </span>
                        <span className="flex items-center gap-1">
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-slate-500">
                            <circle cx="12" cy="12" r="10" />
                            <path d="M12 6v6l4 2" />
                          </svg>
                          {task.duration}
                        </span>
                      </div>
                    </div>
                  </div>
                  <StatusBadge
                    variant={
                      task.status === "completed" ? "safe" :
                      task.status === "snoozed" ? "warning" :
                      "pending"
                    }
                    showPulse={false}
                  >
                    {getStatusLabel(task.status)}
                  </StatusBadge>
                </div>

                <div className="flex items-center gap-2 ml-3">
                  {task.status === "pending" && (
                    <>
                      <Button size="sm" variant="secondary" onClick={() => console.log("Snooze", task.id)}>
                        Snooze
                      </Button>
                      <Button size="sm" variant="primary" onClick={() => console.log("Complete", task.id)}>
                        Complete
                      </Button>
                    </>
                  )}
                  {task.status === "snoozed" && (
                    <Button size="sm" variant="ghost" onClick={() => console.log("Unsnooze", task.id)}>
                      Unsnooze
                    </Button>
                  )}
                  {task.status === "completed" && (
                    <span className="text-emerald-400 text-sm font-medium">✓ Done</span>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>

        {filteredTasks.length === 0 && (
          <Card className="text-center py-12">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="mx-auto text-slate-500 mb-4">
              <path d="M9 11l3 3L22 4" />
              <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
            </svg>
            <p className="text-body text-slate-400">No {filter !== "all" ? filter : ""} tasks</p>
          </Card>
        )}
      </div>
    </MobileLayout>
  );
}