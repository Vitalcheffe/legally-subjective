"use client";

import { create } from "zustand";

interface MatrixState {
  module: string;
  setModule: (m: string) => void;
  selectedJudge: string | null;
  setSelectedJudge: (j: string | null) => void;
}

export const useMatrixStore = create<MatrixState>((set) => ({
  module: "overview",
  setModule: (module) => set({ module }),
  selectedJudge: null,
  setSelectedJudge: (selectedJudge) => set({ selectedJudge }),
}));
