import { atom } from "jotai"

export type FloorPostureFilter = "all" | "red" | "amber" | "green" | "neutral"
export type FloorSeverityFilter = "all" | "red" | "amber" | "neutral"
export type FloorTimeFilter = "all" | "24h" | "7d"
export type FloorActivityFilter = "all" | "active" | "attention" | "blocked" | "completed"

export const floorProjectFilterAtom = atom("all")
export const floorActivityFilterAtom = atom<FloorActivityFilter>("all")
export const floorPostureFilterAtom = atom<FloorPostureFilter>("all")
export const floorSeverityFilterAtom = atom<FloorSeverityFilter>("all")
export const floorTimeFilterAtom = atom<FloorTimeFilter>("all")
export const floorInspectorAtom = atom<string | null>(null)
