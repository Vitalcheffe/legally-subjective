import { MailApp } from "@/components/mail/MailApp";

/**
 * Public entry — INFINITUM, « La Boîte de la Cour ».
 * A shared dossier deep link (?dossier=nyappdiv-<cluster>) opens that real
 * case directly in the reading pane; everything else is the standard mailbox.
 */
export default async function Home({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const raw = params.dossier;
  const initialDossier = (Array.isArray(raw) ? raw[0] : raw) ?? undefined;
  return <MailApp initialDossier={initialDossier} />;
}
