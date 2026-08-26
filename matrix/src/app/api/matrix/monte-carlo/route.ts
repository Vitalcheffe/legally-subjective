import { NextResponse } from "next/server";
import { runMonteCarlo, MonteCarloFilter } from "@/lib/matrix/queries";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  try {
    const body = (await request.json().catch(() => ({}))) as MonteCarloFilter & { iterations?: number };
    const filter: MonteCarloFilter = {
      department: body.department || undefined,
      judge: body.judge || undefined,
      yearFrom: body.yearFrom ? Number(body.yearFrom) : undefined,
      yearTo: body.yearTo ? Number(body.yearTo) : undefined,
      chargeLike: body.chargeLike || undefined,
    };
    const iterations = Math.min(Math.max(Number(body.iterations ?? 10000), 1000), 50000);
    const data = await runMonteCarlo(filter, iterations);
    return NextResponse.json(data);
  } catch (e) {
    return NextResponse.json(
      { empty: true, message: `Erreur d'accès à l'index réel : ${(e as Error).message}` },
      { status: 500 },
    );
  }
}
