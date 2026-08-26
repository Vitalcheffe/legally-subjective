import { NextResponse } from "next/server";
import { createExperiment, listExperiments, getExperimentState } from "@/lib/matrix/experiments";

export const dynamic = "force-dynamic";
export const maxDuration = 60;

export async function GET(request: Request) {
  try {
    const url = new URL(request.url);
    const id = url.searchParams.get("id");
    if (id) {
      const state = await getExperimentState(Number(id));
      return NextResponse.json(state);
    }
    const data = await listExperiments();
    return NextResponse.json(data);
  } catch (e) {
    return NextResponse.json(
      { empty: true, message: `Erreur d'accès à l'index réel : ${(e as Error).message}` },
      { status: 500 },
    );
  }
}

export async function POST(request: Request) {
  try {
    const body = (await request.json().catch(() => ({}))) as {
      targetN?: number;
      seed?: number;
      label?: string;
    };
    const targetN = Math.min(Math.max(Number(body.targetN ?? 10), 5), 40);
    const seed = Number(body.seed ?? 42);
    if (!Number.isFinite(seed)) {
      return NextResponse.json(
        { empty: true, message: "Graine invalide — le protocole exige une graine numérique." },
        { status: 400 },
      );
    }
    const label = (body.label ?? "").slice(0, 80) ||
      `zero-shot n=${targetN} seed=${seed}`;
    const created = await createExperiment(label, targetN, seed);
    const state = await getExperimentState(created.id);
    return NextResponse.json(state, { status: 201 });
  } catch (e) {
    return NextResponse.json(
      { empty: true, message: `Création de protocole impossible : ${(e as Error).message}` },
      { status: 500 },
    );
  }
}
