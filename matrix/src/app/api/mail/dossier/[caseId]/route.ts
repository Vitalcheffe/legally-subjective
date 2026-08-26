import { NextResponse } from "next/server";
import { getDossier, getDigest } from "@/lib/matrix/mailbox";

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ caseId: string }> },
) {
  try {
    const { caseId } = await params;
    if (caseId.startsWith("digest-")) {
      const digest = await getDigest(decodeURIComponent(caseId));
      if (!digest) {
        return NextResponse.json(
          { empty: true, message: `Rapport inconnu : ${caseId} — l'index ne contient que des rapports réels.` },
          { status: 404 },
        );
      }
      return NextResponse.json(digest);
    }
    const dossier = await getDossier(decodeURIComponent(caseId));
    return NextResponse.json(dossier, { status: dossier.empty ? 404 : 200 });
  } catch (e) {
    return NextResponse.json(
      { empty: true, message: `Erreur d'accès au dossier réel : ${(e as Error).message}` },
      { status: 500 },
    );
  }
}
