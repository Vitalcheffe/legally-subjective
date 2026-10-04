#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Legally Subjective — M3b : gestion d'état durable (Colab + Google Drive).

Architecture « écriture locale + promotion atomique + manifeste en dernier »
===========================================================================

Problème. Une session Colab gratuite peut mourir à tout instant (quota,
timeout, onglet fermé, coupure réseau). L'architecture v1 ne survivait qu'au
niveau « juge entier » : un juge de 4-9 h ne pouvait JAMAIS finir dans des
sessions d'une heure, et la reprise passait par un zip téléversé à la main.

Principes (cahier des charges, traduits en invariants) :

  I1  Le filesystem du runtime n'est JAMAIS une source de vérité ; seule
      la racine Drive l'est (racine unique, manifeste unique).
  I2  Un checkpoint n'est OFFICIEL que s'il est référencé par le manifeste
      (ordre d'écriture : fichiers d'abord, manifeste EN DERNIER).
  I3  Toute écriture durable est atomique : tmp + fsync + rename, jamais
      d'écrasement en place. Un état partiellement écrit est invisible
      (préfixe .tmp-) et nettoyé au démarrage suivant.
  I4  Un juge marqué ``done`` possède son adaptateur final sur Drive, dont
      le contenu correspond aux hash enregistrés, et qui a été rechargé +
      vérifié avant le marquage.
  I5  Une reprise ne change JAMAIS la configuration scientifique : l'em-
      preinte (clés scientifiques + données + seed) doit correspondre, sinon
      refus explicite.
  I6  Toutes les opérations sont idempotentes : re-exécuter une cellule ne
      crée ni doublon ni destruction d'état valide.
  I7  En cas d'état illisible/incohérent, le système refuse de repartir de
      zéro silencieusement (des checkpoints présents = du travail payé).

Répertoire Drive (créé automatiquement, à ne JAMAIS renommer/supprimer) :

    <racine>/
      state.json            manifeste = source de vérité unique
      state.json.bak        génération précédente du manifeste
      checkpoints/<juge>/ckpt-<pas>/   checkpoints Trainer promus
      adapters/<juge>/      adaptateurs FINAUX validés (un par juge fait)
      m3b_report.json       rapport DÉRIVÉ du manifeste (jamais édité)
      experiment_manifest.json   LIGNAGE complet (v3, cf. plus bas)
      events.jsonl          journal d'événements append-only (v3)
      evidence/             captures de sorties réelles (v3)
      final/m3b_adapters_final.zip     export final automatique
      log.txt               journal lisible (une ligne par événement)

Le manifeste (schéma m3b-state/3) :

    { "schema", "run_id", "fingerprint", "fingerprint_parts",
      "code": {"head_initial", "heads_seen"},
      "environment": {...}, "environments_seen": [...],
      "seal_checks": [{run_id, ok, sealed_sha256}],
      "judges": {<juge>: {"status": pending|training|done|failed,
                          "step", "ckpt": {"step", "files": {hashes}},
                          "best_step", "best_val_loss", "es_counter",
                          "val_loss_history": [[pas, perte], ...],
                          "n_train", "n_val", "n_tokens_train",
                          "params": {trainable, total}, "steps_total",
                          "wall_seconds", "max_mem_gb",
                          "interruptions", "resumes", "error"}},
      "results": [...], "probe": {...}, "memorization": {...},
      "finalized": bool, "sessions": [...] }

Journal d'événements (events.jsonl) — une ligne JSON par événement réel,
append + fsync, dernière ligne potentiellement incomplète tolérée :

    SESSION_START START CHECKPOINT RESUME RECOVERY VALIDATION ERROR
    JUDGE_COMPLETE RUN_COMPLETE EXPORT NOTE RESET

Lignage (experiment_manifest.json, schéma m3b-manifest/1) : relie
expérience → code (commit + gel du protocole) → données (hash par juge) →
configuration (empreinte) → environnement → checkpoints → adaptateurs →
événements → export final. ``verify_lineage()`` remonte TOUTE la chaîne
et re-calcule chaque hash.

Ce module n'utilise QUE la stdlib ; les callbacks Trainer importent
transformers paresseusement (base de repli neutre si absent) — la logique
d'état est donc testable sans GPU, sans torch, en injection de pannes.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# ------------------------------------------------------------------ ctes --
SCHEMA = "m3b-state/3"
LEGACY_SCHEMAS = ("m3b-state/2",)          # acceptées, sur-places enrichies
CKPT_PREFIX = "ckpt-"
TMP_PREFIX = ".tmp-ckpt-"
MANIFEST_SCHEMA = "m3b-manifest/1"
EVENT_KINDS = ("SESSION_START", "START", "CHECKPOINT", "RESUME",
               "RECOVERY", "VALIDATION", "ERROR", "JUDGE_COMPLETE",
               "RUN_COMPLETE", "EXPORT", "NOTE", "RESET")

# Fichiers attendus dans un checkpoint Trainer complet (reprise exacte :
# poids adaptateur + optimizer + scheduler + RNG + état d'avancement).
CKPT_REQUIRED = ("optimizer.pt", "scheduler.pt", "rng_state.pth",
                 "trainer_state.json")
CKPT_WEIGHTS = ("adapter_model.safetensors", "adapter_model.bin")

# Clés de CONFIG qui définissent la trajectoire scientifique. Toute
# modification entre deux sessions = refus de reprendre. Les clés
# opérationnelles (SAVE_STEPS, SOFT_MINUTES, DRIVE_ROOT) sont exclues :
# elles changent le rythme de sauvegarde, pas l'expérience.
SCI_KEYS = ("MODEL_ID", "MAX_LEN", "INSTR_KEEP", "LORA_R", "LORA_ALPHA",
            "LORA_DROPOUT", "LR", "EPOCHS", "BATCH", "GRAD_ACCUM",
            "EVAL_EVERY", "PATIENCE", "WARMUP", "VAL_FRACTION",
            "MIN_TRAIN_ROWS", "PERSONAS_GARDÉES")


# ------------------------------------------------------------- utilitaires --
def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _fsync_dir(path):
    try:
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        pass                      # plateformes sans fsync de répertoire


def atomic_write_json(path, obj):
    """Écriture atomique : tmp + fsync + rename. Jamais d'écrasement en
    place — un crash laisse l'ancien fichier intact (I3)."""
    path = str(path)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    _fsync_dir(os.path.dirname(path) or ".")


def promote_dir(src, dst):
    """Copie atomique d'un répertoire local vers sa destination finale :
    copie dans .tmp-<nom> puis rename (I3). Un crash laisse la destination
    précédente intacte et un .tmp- orphelin, invisible pour la suite."""
    dst = str(dst)
    parent = os.path.dirname(dst)
    os.makedirs(parent, exist_ok=True)
    tmp = os.path.join(parent, TMP_PREFIX + os.path.basename(dst))
    if os.path.exists(tmp):
        shutil.rmtree(tmp)
    shutil.copytree(src, tmp)
    if os.path.exists(dst):
        shutil.rmtree(dst)
    os.rename(tmp, dst)
    _fsync_dir(parent)


def promote_file(src, dst):
    """Copie atomique d'un FICHIER local vers Drive : copie + fsync dans
    .tmp- puis rename (I3). Le zip final et le rapport passent par ici."""
    dst = str(dst)
    parent = os.path.dirname(dst)
    os.makedirs(parent, exist_ok=True)
    tmp = os.path.join(parent, TMP_PREFIX + os.path.basename(dst))
    if os.path.exists(tmp):
        os.remove(tmp)
    with open(src, "rb") as f, open(tmp, "wb") as g:
        shutil.copyfileobj(f, g, 1 << 20)
        g.flush()
        os.fsync(g.fileno())
    os.replace(tmp, dst)                    # remplacement atomique POSIX
    _fsync_dir(parent)


def safe_rmtree(path):
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
        return True
    except Exception:
        return False


def deterministic_write_zip(zpath, entries):
    """Zip REPRODUCTIBLE octet par octet : métadonnées figées (date 1980,
    attributs fixes), flux streamés. Deux exports du même contenu donnent
    le même sha256 — l'idempotence de l'export devient VÉRIFIABLE (I6).
    Écriture atomique : .tmp puis rename."""
    import zipfile
    zpath = str(zpath)
    tmp = zpath + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for path, arcname in entries:
            zi = zipfile.ZipInfo(arcname, date_time=(1980, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            with z.open(zi, "w") as dst, open(path, "rb") as src:
                shutil.copyfileobj(src, dst, 1 << 20)
    if os.path.exists(zpath):
        os.remove(zpath)
    os.replace(tmp, zpath)


def fingerprint_of(config, sci_keys=SCI_KEYS):
    """Empreinte de la configuration SCIENTIFIQUE seule (I5)."""
    sub = {k: config[k] for k in sci_keys if k in config}
    return hashlib.sha256(
        json.dumps(sub, sort_keys=True, ensure_ascii=False)
        .encode("utf-8")).hexdigest()


def data_fingerprint(personas_dir, judges):
    """Empreinte des données d'entraînement : sha256 de chaque
    personas/<juge>/train.jsonl. Les fichiers de test ne sont JAMAIS
    touchés (loi no-leak : ils restent fermés jusqu'à M4)."""
    parts = {}
    for j in sorted(judges):
        p = os.path.join(str(personas_dir), j, "train.jsonl")
        parts[j] = sha256_file(p) if os.path.isfile(p) else None
    return hashlib.sha256(
        json.dumps(parts, sort_keys=True).encode("utf-8")).hexdigest(), parts


# ------------------------------------------------------- journal public --
def read_events(root):
    """Lit <racine>/events.jsonl : liste d'événements + signal de dernière
    ligne incomplète (crash mid-write) — l'équivalent journal de la
    promotion atomique : un crash ne détruit jamais les lignes d'avant."""
    p = Path(root) / "events.jsonl"
    if not p.exists():
        return [], False
    evts, partial = [], False
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                evts.append(json.loads(line))
            except Exception:
                partial = True            # ligne cassée : ignorée, signalée
    return evts, partial


def events_summary(root):
    evts, partial = read_events(root)
    counts = {}
    for e in evts:
        counts[e.get("kind", "?")] = counts.get(e.get("kind", "?"), 0) + 1
    return {"n_events": len(evts), "counts": counts,
            "first_ts": evts[0]["ts"] if evts else None,
            "last_ts": evts[-1]["ts"] if evts else None,
            "partial_last_line": partial}


# ------------------------------------------------------------ preuves ----
def evidence_dump(root, slug, text, note="", run_id=None, head=None):
    """Capture une sortie RÉELLE (jamais fabriquée) dans <racine>/evidence/.

    Chaque fichier : en-tête (utc, run_id, commit, note) + le texte tel
    que produit par l'exécution. Index JSON mis à jour atomiquement. Les
    captures complètent les journaux machine-readable — ne les remplacent
    jamais. Toute capture fabriquée serait une fraude scientifique."""
    root = Path(root)
    evd = root / "evidence"
    evd.mkdir(parents=True, exist_ok=True)
    idxp = evd / "index.json"
    idx = None
    if idxp.exists():
        try:
            idx = json.load(open(idxp, encoding="utf-8"))
        except Exception:
            idx = None
    if not isinstance(idx, dict) or "captures" not in idx:
        idx = {"schema": "ls-evidence/1", "captures": []}
    seq = max((c.get("seq", 0) for c in idx["captures"]), default=0) + 1
    cid = f"{seq:03d}"
    slug = "".join(ch if ch.isalnum() or ch in "-_" else "-"
                   for ch in str(slug))[:60]
    header = [
        "═" * 60,
        f"CAPTURE {cid} — {slug}",
        f"utc    : {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
    ]
    if run_id:
        header.append(f"run_id : {run_id}")
    if head:
        header.append(f"commit : {head}")
    if note:
        header.append(f"prouve : {note}")
    header += ["─" * 60, "SORTIE RÉELLE NON MODIFIÉE :", ""]
    path = evd / f"{cid}_{slug}.txt"
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("\n".join(header) + str(text) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    idx["captures"].append(
        {"seq": seq, "id": cid, "slug": slug, "note": note,
         "ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
         "run_id": run_id, "file": str(path)})
    atomic_write_json(idxp, idx)
    return path


# ------------------------------------------------------------- scellé ----
def seal_hash_from_stats(stats):
    """Re-calcul du hash du scellé M4 depuis stats_v1.json (méthode
    EXACTE de m15_audit / build_corpus : sha256(json.dumps(cases)))."""
    sel = stats.get("five_four_selection", {})
    cases = sel.get("cases")
    if not cases:
        return None, None
    return (hashlib.sha256(json.dumps(cases).encode()).hexdigest(),
            sel.get("sealed_sha256"))


def seal_check_from_repo(repo_path):
    """Re-vérifie le scellé dans le clone COURANT : {ok, sealed_sha256,
    n_cases}. Retourne ok=None si stats_v1.json est introuvable (le §5bis
    refusera de démarrer si le scellé n'est pas vérifiable)."""
    p = os.path.join(str(repo_path), "data", "processed", "stats_v1.json")
    if not os.path.isfile(p):
        return {"ok": None, "why": "stats_v1.json introuvable", "path": p}
    try:
        stats = json.load(open(p, encoding="utf-8"))
    except Exception as e:
        return {"ok": None, "why": f"stats_v1.json illisible : {e}", "path": p}
    rec, ref = seal_hash_from_stats(stats)
    n = len(stats.get("five_four_selection", {}).get("cases", []))
    ok = bool(rec and ref and rec == ref and n == 50)
    return {"ok": ok, "sealed_sha256": ref,
            "recomputed": rec, "n_cases": n,
            "source": "data/processed/stats_v1.json"}


# ------------------------------------------------------------------ état --
class ExpState:
    """Le manifeste vivant de l'expérience M3b. Source de vérité unique."""

    def __init__(self, root, log_path=None):
        self.root = Path(root)
        self.path = self.root / "state.json"
        self.bak = self.root / "state.json.bak"
        self.events_path = self.root / "events.jsonl"
        self.log_path = Path(log_path) if log_path else self.root / "log.txt"
        self.state = None

    # ------------------------------------------------------------ journal --
    def log(self, msg):
        line = f"[{time.strftime('%H:%M:%S')}] {msg}"
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass
        print(line)

    # ------------------------------------------------- journal d'événements --
    @staticmethod
    def _ends_with_newline(p):
        """Le journal se termine-t-il par un \n ? (une écriture déchirée
        par un crash laisse la dernière ligne sans retour — coller un
        nouvel enregistrement dessus fusionnerait deux lignes en une
        illisible : on repart d'une ligne neuve.)"""
        try:
            with open(p, "rb") as f:
                f.seek(0, os.SEEK_END)
                if f.tell() == 0:
                    return True
                f.seek(-1, os.SEEK_END)
                return f.read(1) == b"\n"
        except OSError:
            return True

    def event(self, kind, **fields):
        """Append une ligne JSON datée à events.jsonl (fsync). Le journal
        est un TÉMOIN append-only : son échec d'écriture n'interrompt
        jamais l'expérience (le manifeste reste la source de vérité)."""
        if kind not in EVENT_KINDS:
            raise ValueError(f"type d'événement inconnu : {kind}")
        rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "kind": kind}
        if self.state is not None:
            rec["run_id"] = self.state.get("run_id")
        rec.update({k: v for k, v in fields.items() if v is not None})
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            with open(self.events_path, "a", encoding="utf-8") as f:
                if not self._ends_with_newline(self.events_path):
                    f.write("\n")            # répare la ligne déchirée
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                f.flush()
                os.fsync(f.fileno())
        except OSError:
            pass
        shown = " ".join(f"{k}={v}" for k, v in fields.items()
                         if k not in ("files",) and v is not None)
        self.log(f"événement {kind} {shown}".rstrip())

    def read_events(self):
        """Lit events.jsonl en tolérant une dernière ligne cassée par un
        crash (elle est ignorée et signalée) — équivalent journal de la
        promotion atomique des checkpoints."""
        return read_events(self.root)

    # ------------------------------------------------------ chargement ----
    def _read_json(self, p):
        try:
            return json.load(open(p, encoding="utf-8"))
        except Exception:
            return None

    def load_or_init(self, fingerprint, parts, seed, repo_head, judges,
                     run_id, env=None, seal=None):
        """Charge le manifeste ou crée-le vierge.

        ``env``   : dict versions/matériel capturé au début de session
                    (python, torch, transformers, peft, bnb, gpu…) ;
        ``seal``  : dict {ok, sealed_sha256} — scellé M4 re-vérifié dans le
                    clone COURANT (preuve que cette session tourne avec la
                    chaîne de scellement intacte).

        Retour (mode, message) :
          "fresh"   — aucune expérience commencée (distinction sans
                      ambiguïté, exigence 12 du cahier des charges) ;
          "resume"  — état cohérent trouvé ;
          "error"   — état illisible/incohérent avec checkpoints présents :
                      REFUS de repartir de zéro silencieusement (I7).
        """
        self.root.mkdir(parents=True, exist_ok=True)
        st = None
        if self.path.exists():
            st = self._read_json(self.path)
            if st is None:                       # JSON corrompu → .bak
                self.log("state.json illisible — essai de state.json.bak")
                st = self._read_json(self.bak)
        elif self.bak.exists():                  # manifeste perdu, bak vivant
            st = self._read_json(self.bak)
            if st is not None:
                self.log("state.json absent — récupéré depuis .bak")
                self.event("RECOVERY", detail="state.json récupéré depuis .bak")
        if st is not None and (not isinstance(st, dict)
                               or st.get("schema") not in
                               (SCHEMA,) + LEGACY_SCHEMAS):
            st = None

        if st is None:
            if self._has_checkpoints():
                self.event("ERROR", detail=(
                    "checkpoints présents mais manifeste illisible/absent "
                    "(I7 — refus de repartir de zéro)"))
                return "error", (
                    "checkpoints présents mais manifeste illisible/absent — "
                    "refus de repartir de zéro (I7 : ce serait jeter du "
                    "travail payé sans le dire). NE PAS relancer "
                    "l'entraînement tel quel : envoyer le diagnostic "
                    "(log.txt + contenu de checkpoints/).")
            self.state = {
                "schema": SCHEMA, "run_id": run_id,
                "fingerprint": fingerprint, "fingerprint_parts": parts,
                "seed": seed,
                "code": {"head_initial": repo_head,
                         "heads_seen": [repo_head]},
                "environment": env,
                "environments_seen": [env] if env else [],
                "seal_checks": [dict(seal, run_id=run_id)] if seal else [],
                "judges": {j: self._blank_judge() for j in judges},
                "results": [], "probe": None, "memorization": None,
                "finalized": False, "sessions": [],
            }
            self.save()
            self.event("SESSION_START", mode="fresh", head=repo_head,
                       judges=len(judges), seed=seed)
            return "fresh", "aucune expérience commencée — départ propre"

        # --- reprise : mise à niveau v2 → v3 (enrichissement, zéro perte) --
        if st.get("schema") in LEGACY_SCHEMAS:
            for j, v in st.get("judges", {}).items():
                base = self._blank_judge()
                base.update(v)
                st["judges"][j] = base
            st.setdefault("environment", None)
            st.setdefault("environments_seen", [])
            st.setdefault("seal_checks", [])
            st["schema"] = SCHEMA
            self.log("manifeste v2 → v3 enrichi (aucun changement "
                     "scientifique — champs statistiques ajoutés)")

        # --- reprise : contrôles d'intégrité scientifique (I5) -----------
        if st.get("fingerprint") != fingerprint:
            self.event("ERROR", detail="empreinte incompatible — refus")
            return "error", (
                "EMPREINTE INCOMPATIBLE : la configuration scientifique ou "
                "les données ont changé depuis le début de l'expérience. "
                "Reprendre mélangerait deux expériences différentes. "
                "Si le changement est DÉLIBÉRÉ : cellule RESET TOTAL, tout "
                "réentraîner. Sinon : ne rien modifier (CONFIG et données "
                "personas doivent rester strictement identiques).")
        st.setdefault("judges", {})
        for j in judges:
            st["judges"].setdefault(j, self._blank_judge())
        st.setdefault("results", [])
        st.setdefault("finalized", False)
        st.setdefault("sessions", [])
        st.setdefault("code", {}).setdefault("heads_seen", [])
        st.setdefault("environments_seen", [])
        st.setdefault("seal_checks", [])
        if repo_head and repo_head not in st["code"]["heads_seen"]:
            st["code"]["heads_seen"].append(repo_head)
            self.log(f"note : nouveau HEAD repo vu ({repo_head[:10]}) — "
                     "enregistré (le code du protocole, lui, est gelé au "
                     "tag m4-freeze côté M4)")
        if env:
            st["environments_seen"].append(
                {"run_id": run_id, **env})
            del st["environments_seen"][:-20]         # borné, utile seulement
        if seal:
            st["seal_checks"].append(dict(seal, run_id=run_id))

        # --- interruptions détectées : juges laissés « training » par la
        #     session précédente (mort brutale ou budget) → comptés, puis
        #     rendus « pending » (ils ne sont PAS en entraînement maintenant)
        n_int = 0
        for j, v in st["judges"].items():
            if v.get("status") == "training":
                v["interruptions"] = (v.get("interruptions") or 0) + 1
                v["status"] = "pending"
                n_int += 1
                self.event("RECOVERY", judge=j,
                           detail=("interruption détectée au démarrage "
                                   f"(total {v['interruptions']}) — reprendra "
                                   "depuis son checkpoint"))
        self.state = st
        self.save()
        self.event("SESSION_START", mode="resume", head=repo_head,
                   done=self.done_count(), total=len(st["judges"]),
                   interruptions_detected=n_int,
                   seal_ok=(seal or {}).get("ok"))
        return "resume", self.summary()

    @staticmethod
    def _blank_judge():
        return {"status": "pending", "step": 0, "ckpt": None,
                "best_step": None, "best_val_loss": None, "es_counter": 0,
                "val_loss_history": [],
                "n_train": None, "n_val": None, "n_tokens_train": None,
                "params": None, "steps_total": None,
                "wall_seconds": 0.0, "max_mem_gb": None,
                "interruptions": 0, "resumes": 0, "error": None}

    def _has_checkpoints(self):
        d = self.root / "checkpoints"
        return d.is_dir() and any(d.iterdir())

    # -------------------------------------------------------- écriture ----
    def save(self):
        """Sauvegarde atomique + conservation de la génération précédente
        (I3) : .bak = avant-dernier état cohérent connu."""
        if self.state is None:
            return
        if self.path.exists():
            try:
                shutil.copy2(self.path, str(self.bak))
            except OSError:
                pass
        atomic_write_json(self.path, self.state)

    # --------------------------------------------------------- accès ------
    def j(self, name):
        if self.state is None:
            raise RuntimeError("état non chargé (mode error) — voir le "
                               "message de load_or_init ; ne rien contourner")
        return self.state["judges"].setdefault(name, self._blank_judge())

    def status(self, name):
        return self.j(name)["status"]

    def set_status(self, name, s):
        self.j(name)["status"] = s

    def fail(self, name, err):
        self.j(name)["error"] = str(err)[:200]
        self.j(name)["status"] = "failed"
        self.event("ERROR", judge=name, error=str(err)[-160:])

    def step(self, name):
        return self.j(name).get("step") or 0

    def all_done(self, judges=None):
        if self.state is None:                    # mode error : rien n'est fini
            return False
        js = self.state["judges"] if judges is None \
            else {k: v for k, v in self.state["judges"].items()
                  if k in judges}
        return bool(js) and all(v.get("status") == "done" for v in js.values())

    def done_count(self):
        if self.state is None:
            return 0
        return sum(1 for v in self.state["judges"].values()
                   if v.get("status") == "done")

    # ------------------------------------------------- checkpoints Drive --
    def ckpt_dir(self, name):
        return self.root / "checkpoints" / name

    def _hash_local_ckpt(self, local_dir):
        out = {}
        for fn in sorted(os.listdir(local_dir)):
            p = os.path.join(local_dir, fn)
            if os.path.isfile(p):
                out[fn] = sha256_file(p)
        return out

    def register_and_promote(self, name, step, local_ckpt_dir):
        """Fait d'un checkpoint local Trainer le checkpoint OFFICIEL :
        copie atomique vers Drive, hash des fichiers, PUIS manifeste
        (I2 : le manifeste n'apparaît qu'après les fichiers)."""
        step = int(step)
        local = str(local_ckpt_dir)
        missing = [f for f in CKPT_REQUIRED
                   if not os.path.isfile(os.path.join(local, f))]
        if missing:
            raise RuntimeError(
                f"checkpoint local incomplet ({name}, pas {step}) : "
                f"manque {missing} — rien n'est promu (I4)")
        hashes = self._hash_local_ckpt(local)
        dst = self.ckpt_dir(name) / f"{CKPT_PREFIX}{step}"
        promote_dir(local, dst)
        self.j(name)["ckpt"] = {"step": step,
                                "files": hashes}
        self.j(name)["step"] = step
        self.save()
        self.event("CHECKPOINT", judge=name, step=step,
                   n_files=len(hashes),
                   mo=round(sum(os.path.getsize(os.path.join(local, f))
                                for f in hashes) / 1e6))
        self.log(f"ckpt promu : {name} pas {step} "
                 f"({sum(os.path.getsize(os.path.join(local, f)) for f in hashes) / 1e6:.0f} Mo)")
        return dst

    def prune_ckpts(self, name, keep=2):
        """Garde les 2 générations les plus récentes + la meilleure ;
        supprime le reste et tous les .tmp- orphelins (I3, minimisation
        de l'occupation Drive)."""
        d = self.ckpt_dir(name)
        if not d.is_dir():
            return
        keep_steps = set()
        best = self.j(name).get("best_step")
        if keep > 0 and best:
            keep_steps.add(int(best))
        gens = []
        for p in d.iterdir():
            if p.name.startswith(TMP_PREFIX):
                safe_rmtree(p)
            elif p.name.startswith(CKPT_PREFIX):
                try:
                    gens.append((int(p.name[len(CKPT_PREFIX):]), p))
                except ValueError:
                    pass
        gens.sort(reverse=True)
        keep_steps |= {s for s, _ in gens[:keep]}
        for s, p in gens:
            if s not in keep_steps:
                safe_rmtree(p)
        # entry obsolète ? la retirer du manifeste
        e = self.j(name).get("ckpt")
        if e and not (d / f"{CKPT_PREFIX}{e['step']}").is_dir():
            self.j(name)["ckpt"] = None

    def clean_tmp(self):
        d = self.root / "checkpoints"
        if not d.is_dir():
            return 0
        n = 0
        for juge in d.iterdir():
            if not juge.is_dir():
                continue
            for p in juge.iterdir():
                if p.name.startswith(TMP_PREFIX):
                    safe_rmtree(p)
                    n += 1
        if n:
            self.log(f"nettoyage : {n} promotion(s) interrompue(s) "
                     "supprimée(s) (.tmp-)")
        return n

    def verify_drive_entry(self, entry, name=None):
        """Vérifie qu'un checkpoint officiel est INTÈGRE sur Drive (hash
        par fichier). Retourne (ok, raison)."""
        if not entry:
            return False, "aucun checkpoint enregistré"
        d = self.ckpt_dir(name) / f"{CKPT_PREFIX}{entry['step']}"
        if not d.is_dir():
            return False, f"répertoire {d.name} absent"
        for fn, h in entry["files"].items():
            p = d / fn
            if not p.is_file():
                return False, f"{fn} absent"
            if sha256_file(p) != h:
                return False, f"{fn} : hash divergent (corruption)"
        miss = [f for f in CKPT_REQUIRED
                if f not in entry["files"]]
        if miss:
            return False, f"fichiers requis manquants : {miss}"
        return True, "intègre"

    def restore_ckpt_local(self, name, local_parent):
        """Rapatrie le checkpoint officiel vers le disque local et le
        VÉRIFIE sur la copie (la vérification locale teste aussi la copie).
        En cas de corruption : essaie les générations précédentes restées
        sur Drive. Retourne le chemin local du checkpoint à passer à
        Trainer(resume_from_checkpoint=...), ou None."""
        entry = self.j(name).get("ckpt")
        d = self.ckpt_dir(name)
        if not entry or not d.is_dir():
            return None
        gens = []
        for p in d.iterdir():
            if p.name.startswith(CKPT_PREFIX):
                try:
                    gens.append((int(p.name[len(CKPT_PREFIX):]), p))
                except ValueError:
                    pass
        gens.sort(reverse=True)
        wanted = int(entry["step"])
        order = [g for g in gens if g[0] == wanted] + \
                [g for g in gens if g[0] != wanted]
        local_parent = Path(local_parent)
        local_parent.mkdir(parents=True, exist_ok=True)
        for step, _ in order:
            src = d / f"{CKPT_PREFIX}{step}"
            dst = local_parent / f"{CKPT_PREFIX}{step}"
            if dst.exists():
                safe_rmtree(dst)
            try:
                shutil.copytree(src, dst)
            except Exception as e:
                self.log(f"copie impossible {name}@{step} : {e}")
                continue
            # -- vérification SUR LA COPIE (teste aussi la copie elle-même)
            bad = []
            for fn in CKPT_REQUIRED:
                if not (dst / fn).is_file():
                    bad.append(fn)
            if step == wanted:            # génération officielle : hash
                for fn, h in entry["files"].items():
                    p = dst / fn
                    if p.is_file() and sha256_file(p) != h:
                        bad.append(fn + " (hash)")
            if bad:
                self.log(f"checkpoint {name}@{step} invalide ({bad}) — "
                         "génération précédente essayée")
                safe_rmtree(dst)
                continue
            if step != wanted:            # fallback : devient l'officiel
                self.j(name)["ckpt"] = {"step": step,
                                        "files": self._hash_local_ckpt(dst)}
                self.j(name)["step"] = step
                self.save()
                self.event("RECOVERY", judge=name,
                           detail=(f"checkpoint officiel (pas {wanted}) "
                                   f"invalide — repli sur le pas {step}, "
                                   "promu nouvel officiel"))
            self.j(name)["resumes"] = (self.j(name).get("resumes") or 0) + 1
            self.event("RESUME", judge=name, from_step=step)
            self.log(f"reprise : {name} depuis le pas {step}")
            return str(dst)
        self.log(f"aucun checkpoint récupérable pour {name} — "
                 "reprise depuis zéro pour CE juge (consigné)")
        self.event("NOTE", judge=name,
                   detail="aucun checkpoint récupérable — redépart consigné")
        self.j(name)["ckpt"] = None
        self.save()
        return None

    # ------------------------------------------------- adaptateurs finaux --
    def final_adapter_dir(self, name):
        return self.root / "adapters" / name

    def promote_final_adapter(self, name, local_dir):
        """Adaptateur final : promotion atomique + hash + manifeste (I4)."""
        dst = self.final_adapter_dir(name)
        promote_dir(local_dir, dst)
        files = {fn: sha256_file(dst / fn)
                 for fn in sorted(os.listdir(dst))
                 if (dst / fn).is_file()}
        if not any(w in files for w in CKPT_WEIGHTS):
            raise RuntimeError(
                f"adaptateur final de {name} sans poids LoRA — promotion "
                "refusée (I4)")
        self.j(name)["final_adapter"] = {"files": files}
        self.save()
        self.event("VALIDATION", judge=name, stage="adapter_promoted",
                   n_files=len(files), ok=True)
        return dst

    def record_validation(self, name, stage, ok, detail=None):
        """Consigne une étape de validation réelle (rechargement, forward,
        vérification de hash…) dans le journal d'événements."""
        self.event("VALIDATION", judge=name, stage=stage, ok=bool(ok),
                   detail=detail)

    def verify_final_adapter(self, name):
        """Vérifie l'adaptateur final présent sur Drive contre ses hash
        (utilisé avant l'export et par le runner M4)."""
        e = self.j(name).get("final_adapter")
        d = self.final_adapter_dir(name)
        if not e or not d.is_dir():
            return False, "absent du manifeste ou du Drive"
        for fn, h in e["files"].items():
            p = d / fn
            if not p.is_file() or sha256_file(p) != h:
                return False, f"{fn} divergent"
        return True, "intègre"

    # ---------------------------------------------------- finalisation ----
    def mark_done(self, name, result_row):
        row = dict(result_row)
        row["persona"] = name
        row["verified"] = True
        self.state["results"] = [r for r in self.state["results"]
                                 if r.get("persona") != name] + [row]
        j = self.j(name)
        j["status"] = "done"
        j["error"] = None
        self.save()
        self.event("JUDGE_COMPLETE", judge=name,
                   best_step=j.get("best_step"),
                   best_val_loss=j.get("best_val_loss"),
                   last_step=j.get("step"),
                   interruptions=j.get("interruptions"),
                   resumes=j.get("resumes"))

    def derive_report(self, config):
        """m3b_report.json est DÉRIVÉ du manifeste — jamais l'inverse
        (source de vérité unique). Format compatible runner M4/R6."""
        return {
            "config": config,
            "model": config.get("MODEL_ID"),
            "run_id": self.state.get("run_id"),
            "results": self.state.get("results", []),
            "probe": self.state.get("probe"),
            "memorization": self.state.get("memorization"),
            "sessions": len(self.state.get("sessions", [])),
            "state_schema": SCHEMA,
        }

    def write_report(self, config, local_path=None):
        rep = self.derive_report(config)
        atomic_write_json(self.root / "m3b_report.json", rep)
        if local_path:
            atomic_write_json(local_path, rep)
        return rep

    # ----------------------------------------------------------- reset ----
    def reset(self, confirm):
        """RESET TOTAL : renomme la racine Drive (sauvegarde de dernier
        recours) plutôt que de supprimer immédiatement. I6 : rien de
        silencieux."""
        if confirm != "je-veux-tout-effacer":
            return False, ("confirmation absente — RESET annulé ( taper "
                           "exactement : je-veux-tout-effacer )")
        self.event("RESET", detail=str(self.root))
        self.state = None
        dest = str(self.root) + "-DELETED-" + time.strftime("%Y%m%d_%H%M%S")
        try:
            if self.root.exists():
                os.rename(self.root, dest)
            return True, (f"racine renommée vers {os.path.basename(dest)} "
                          "— l'expérience repartira vierge à la prochaine "
                          "cellule d'état")
        except OSError as e:
            return False, f"rename impossible : {e}"

    # ---------------------------------------------------------- statut ----
    def summary(self):
        if self.state is None:
            return "ÉTAT : NON CHARGÉ — mode erreur (voir message au-dessus)"
        js = self.state["judges"]
        done = sum(1 for v in js.values() if v["status"] == "done")
        n = len(js)
        if self.state.get("finalized"):
            head = "ÉTAT : TERMINÉ — expérience finalisée"
        elif done == 0:
            head = "ÉTAT : COMMENCÉE, aucun juge terminé"
        elif done < n:
            head = f"ÉTAT : EN COURS — {done}/{n} juges terminés"
        else:
            head = f"ÉTAT : {n}/{n} juges terminés — finalisation restante"
        lines = [head]
        for name, v in sorted(js.items()):
            info = f"  {name:14s} {v['status']:8s}"
            if v["status"] in ("training", "failed") and v.get("step"):
                info += f" — dernier pas durable : {v['step']}"
            if v.get("best_val_loss") is not None:
                info += f" — best val loss {v['best_val_loss']}"
            if v.get("error"):
                info += f" — dernière erreur : {v['error'][:80]}"
            lines.append(info)
        return "\n".join(lines)


# ------------------------------------------------------------ callbacks --
def _callback_base():
    try:
        from transformers import TrainerCallback
        return TrainerCallback
    except Exception:                       # tests CPU / hors torch :
        # même contrat que TrainerCallback : toutes les méthodes d'événement
        # existent en no-op — les sous-classes n'ont rien à redéfinir.
        class _Plain:
            def on_init_end(self, *a, **k): pass
            def on_train_begin(self, *a, **k): pass
            def on_train_end(self, *a, **k): pass
            def on_epoch_begin(self, *a, **k): pass
            def on_epoch_end(self, *a, **k): pass
            def on_step_begin(self, *a, **k): pass
            def on_substep_end(self, *a, **k): pass
            def on_step_end(self, *a, **k): pass
            def on_evaluate(self, *a, **k): pass
            def on_predict(self, *a, **k): pass
            def on_save(self, *a, **k): pass
            def on_log(self, *a, **k): pass
        return _Plain


class DriveSyncCallback(_callback_base()):
    """Promeut chaque checkpoint Trainer local vers Drive (atomique) et
    met à jour le manifeste — le GPU respire pendant la copie (~1-2 min
    tous les SAVE_STEPS pas), c'est le prix de la durabilité. Les ckpts
    locaux plus anciens sont supprimés après promotion : le disque
    /content reste plat, la vérité est sur Drive."""

    def __init__(self, estate, judge):
        self.es, self.judge = estate, judge

    def on_save(self, args, state, control, **kwargs):
        import os as _os
        ck = _os.path.join(args.output_dir,
                           f"checkpoint-{state.global_step}")
        if not _os.path.isdir(ck):
            return
        self.es.register_and_promote(self.judge, state.global_step, ck)
        self.es.prune_ckpts(self.judge)
        # ménage local : seuls le ckpt fraîchement promu reste en /content
        for p in _os.listdir(args.output_dir):
            if p.startswith("checkpoint-"):
                full = _os.path.join(args.output_dir, p)
                try:
                    if p != f"checkpoint-{state.global_step}":
                        shutil.rmtree(full)
                except OSError:
                    pass


class TimeBudgetCallback(_callback_base()):
    """Transforme une mort brutale en arrêt PROPRE : au soft-deadline, on
    demande une sauvegarde immédiate PUIS l'arrêt (le Trainer sauvegarde
    le pas courant avant de sortir)."""

    def __init__(self, soft_minutes, estate=None):
        self.soft = float(soft_minutes) * 60.0
        self.t0 = time.time()
        self.stopped_by_budget = False

    def on_step_end(self, args, state, control, **kwargs):
        if self.soft <= 0:
            return
        if time.time() - self.t0 > self.soft:
            control.should_save = True
            control.should_training_stop = True
            self.stopped_by_budget = True


class StatefulEarlyStopping(_callback_base()):
    """Early stopping + suivi du meilleur pas, dont l'état VIT DANS LE
    MANIFESTE : le compteur et le best_val_loss survivent aux sessions
    (le callback HF ne sérialise pas son compteur de façon portable)."""

    def __init__(self, estate, judge, patience):
        self.es, self.judge, self.patience = estate, judge, patience
        j = estate.j(judge)
        self.best = j.get("best_val_loss")
        self.counter = j.get("es_counter") or 0

    def on_evaluate(self, args, state, control, metrics=None, **kwargs):
        metrics = metrics or {}
        loss = metrics.get("eval_loss")
        if loss is None:
            return
        j = self.es.j(self.judge)
        hist = j.setdefault("val_loss_history", [])
        hist.append([int(state.global_step), round(float(loss), 4)])
        del hist[:-300]                    # borné : trace, pas un substitut
        if self.best is None or loss < self.best - 1e-4:
            self.best = loss
            self.counter = 0
            j["best_val_loss"] = round(float(loss), 4)
            j["best_step"] = int(state.global_step)
        else:
            self.counter += 1
        j["es_counter"] = self.counter
        self.es.save()
        if self.counter >= self.patience:
            control.should_training_stop = True


# ----------------------------------------------------------- harnais ------
class FakeControl:
    """Imitation minimale de transformers.TrainerControl pour les tests
    d'injection de pannes (mêmes attributs, mêmes effets)."""

    def __init__(self):
        self.should_save = False
        self.should_eval = False
        self.should_log = False
        self.should_training_stop = False
        self.should_epoch_stop = False


class FakeRun:
    """Boucle d'entraînement factice fidèle à l'ordre des événements HF
    Trainer : on_step_end → (save → on_save) → (eval → on_evaluate) →
    arrêt. Sert à tester les callbacks RÉELS sans torch."""

    def __init__(self, callbacks, total_steps, save_steps, eval_steps,
                 loss_fn, output_dir):
        self.callbacks = callbacks
        self.total = total_steps
        self.save_steps, self.eval_steps = save_steps, eval_steps
        self.loss_fn = loss_fn
        self.step_hook = None            # injecté par le harnais (morts)
        self.output_dir = output_dir     # = args.output_dir du Trainer

    def run(self, resume_step=0, ckpt_writer=None):
        control, st = FakeControl(), type("S", (), {})()
        args = type("A", (), {"output_dir": self.output_dir})()
        st.global_step = resume_step
        for step in range(resume_step + 1, self.total + 1):
            if self.step_hook:
                self.step_hook(step)
            st.global_step = step
            for cb in self.callbacks:
                cb.on_step_end(args, st, control)
            if control.should_save or step % self.save_steps == 0:
                if ckpt_writer:
                    ckpt_writer(step)          # fichiers réels (local)
                for cb in self.callbacks:
                    cb.on_save(args, st, control)
            if control.should_eval or step % self.eval_steps == 0:
                metrics = {"eval_loss": self.loss_fn(step)}
                for cb in self.callbacks:
                    cb.on_evaluate(args, st, control,
                                   metrics=metrics)
            if control.should_training_stop:
                return step, "stopped"
        return self.total, "finished"


# ------------------------------------------------------------- lignage ------
def _git(repo, *args):
    try:
        return subprocess.run(["git", "-C", str(repo), *args],
                              capture_output=True, text=True,
                              timeout=20).stdout.strip()
    except Exception:
        return ""


def build_experiment_manifest(estate, config, env_info, repo_path):
    """Construit le MANIFESTE DE LIGNAGE (m3b-manifest/1) sur le Drive.

    Relie, par des hash re-vérifiables :
      expérience → code (commit + gel du protocole) → données (hash/juge)
      → configuration (empreinte + seed) → environnement → checkpoints →
      adaptateurs → événements → export final.
    Écrit atomiquement à <racine>/experiment_manifest.json. Retourne le
    manifeste (dict). Aucune valeur n'est jamais inventée : tout est lu ou
    re-calculé depuis l'état réel."""
    st = estate.state
    repo = Path(repo_path)

    def _fhash(rel):
        p = repo / rel
        return sha256_file(p) if p.is_file() else None

    freeze_sha = _fhash(os.path.join("results",
                                     "protocol_m3b_freeze.json"))
    seal = seal_check_from_repo(repo)
    data_dir = repo / "data" / "m3" / "personas"
    data_parts = {}
    if data_dir.is_dir():
        for j in sorted(st.get("judges", {})):
            p = data_dir / j / "train.jsonl"
            data_parts[j] = sha256_file(p) if p.is_file() else None

    judges_out = {}
    for j, v in st.get("judges", {}).items():
        judges_out[j] = {
            "status": v.get("status"),
            "n_train": v.get("n_train"), "n_val": v.get("n_val"),
            "n_tokens_train": v.get("n_tokens_train"),
            "params": v.get("params"), "steps_total": v.get("steps_total"),
            "best_step": v.get("best_step"),
            "best_val_loss": v.get("best_val_loss"),
            "last_step": v.get("step"),
            "wall_seconds": v.get("wall_seconds"),
            "max_mem_gb": v.get("max_mem_gb"),
            "interruptions": v.get("interruptions"),
            "resumes": v.get("resumes"),
            "val_loss_history_len": len(v.get("val_loss_history") or []),
            "adapter_files": (v.get("final_adapter") or {}).get("files"),
        }

    zf = estate.root / "final" / "m3b_adapters_final.zip"
    artifacts = {}
    if zf.is_file():
        artifacts["final_zip"] = {"path": "final/m3b_adapters_final.zip",
                                  "sha256": sha256_file(zf),
                                  "size": zf.stat().st_size}
    rp = estate.root / "m3b_report.json"
    if rp.is_file():
        artifacts["report"] = {"path": "m3b_report.json",
                               "sha256": sha256_file(rp)}

    manifest = {
        "schema": MANIFEST_SCHEMA,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "experiment": {
            "name": "M3b-persona-qlora",
            "project": "legally-subjective",
            "run_id": st.get("run_id"),
        },
        "protocol": {
            "sci_config": {k: config[k] for k in SCI_KEYS if k in config},
            "fingerprint": st.get("fingerprint"),
            "fingerprint_parts": st.get("fingerprint_parts"),
            "seed": st.get("seed"),
            "data_train_sha256": data_parts,
            "corpus_rule_ref": "docs/02-CORPUS.md + "
                               "data/processed/stats_v1.json",
        },
        "code": {
            "head_initial": st.get("code", {}).get("head_initial"),
            "heads_seen": st.get("code", {}).get("heads_seen"),
            "git_describe": _git(repo, "describe", "--tags", "--always"),
            "m4_freeze_ancestor": None,      # rempli ci-dessous
            "protocol_freeze_sha256": freeze_sha,
            "protocol_freeze_file": "results/protocol_m3b_freeze.json",
            "m3b_state_schema": SCHEMA,
        },
        "environment": st.get("environment"),
        "environments_seen_n": len(st.get("environments_seen") or []),
        "seal_check": seal,
        "seal_checks_n": len(st.get("seal_checks") or []),
        "judges": judges_out,
        "events": events_summary(estate.root),
        "sessions": len(st.get("sessions") or []),
        "finalized": st.get("finalized"),
        "artifacts": artifacts,
    }
    # m4-freeze ancêtre du HEAD courant ? (le protocole M4 n'a pas bougé
    # depuis le gel — le code d'entraînement vit après le tag, le scellé,
    # lui, est vérifié par seal_check)
    mb = subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor",
                         "m4-freeze", "HEAD"], capture_output=True)
    manifest["code"]["m4_freeze_ancestor"] = (mb.returncode == 0)

    atomic_write_json(estate.root / "experiment_manifest.json", manifest)
    return manifest


def verify_lineage(root, repo):
    """Remonte TOUTE la chaîne de preuve et re-calcule chaque hash.

    résultat → prédiction → modèle → checkpoint → configuration → données
    → split → commit → environnement → journal.

    Retourne (liens, ok_global) : liens = liste (ok, nom, détail) dans
    l'ordre de la chaîne. Les checks G8 (exclusion du scellé) et
    métriques relèvent du portillon (m3b_gate.py) — ici, c'est le LIGNAGE
    matière qui est vérifié."""
    root, repo = Path(root), Path(repo)
    links = []

    def add(ok, name, detail=""):
        links.append((bool(ok), name, str(detail)))

    man_p = root / "experiment_manifest.json"
    man = None
    if man_p.is_file():
        try:
            man = json.load(open(man_p, encoding="utf-8"))
        except Exception as e:
            add(False, "L1.manifeste_lisible", f"JSON cassé : {e}")
    add(man is not None, "L1.manifeste_présent",
        man_p if man is None else
        f"schéma {man.get('schema')}")
    if man is None:
        return links, False
    add(man.get("schema") == MANIFEST_SCHEMA, "L1.manifeste.schéma",
        man.get("schema"))

    st_p = root / "state.json"
    st = json.load(open(st_p, encoding="utf-8")) if st_p.is_file() else None
    add(st is not None, "L2.manifeste_état_présent", st_p)
    if st is None:
        return links, False
    add(st.get("schema") == SCHEMA, "L2.état.schéma", st.get("schema"))
    add(st.get("finalized") is True, "L2.état.finalisé", st.get("finalized"))

    # --- L3 : ré-derivation déterministe de l'empreinte -------------------
    sci = man["protocol"]["sci_config"]
    fp_cfg = fingerprint_of(sci)
    fp_dat, parts = data_fingerprint(repo / "data" / "m3" / "personas",
                                     list(man["judges"]))
    combined = hashlib.sha256(json.dumps(
        {"cfg": fp_cfg, "data": fp_dat, "seed": man["protocol"]["seed"]},
        sort_keys=True).encode()).hexdigest()
    add(fp_cfg == st["fingerprint_parts"]["config"],
        "L3.empreinte.config_recalculée",
        f"{fp_cfg[:12]}… vs {st['fingerprint_parts']['config'][:12]}…")
    add(fp_dat == st["fingerprint_parts"]["data"],
        "L3.empreinte.données_recalculées",
        f"{fp_dat[:12]}… vs {st['fingerprint_parts']['data'][:12]}…")
    add(combined == st["fingerprint"],
        "L3.empreinte.globale", f"{combined[:12]}…")

    # --- L4 : adaptateurs finaux, hash par fichier ------------------------
    for j, jm in sorted(man["judges"].items()):
        files = jm.get("adapter_files") or {}
        d = root / "adapters" / j
        if not files or not d.is_dir():
            add(False, f"L4.adaptateur.{j}", "absent du manifeste/Drive")
            continue
        bad = [fn for fn, h in files.items()
               if not (d / fn).is_file() or sha256_file(d / fn) != h]
        add(not bad, f"L4.adaptateur.{j}",
            f"{len(files)} fichiers, divergents : {bad or 'aucun'}")

    # --- L5 : journal d'événements cohérent --------------------------------
    evts, partial = read_events(root)
    jc = {e.get("judge") for e in evts if e["kind"] == "JUDGE_COMPLETE"}
    add(jc == set(man["judges"]), "L5.journal.juges_complétés",
        f"{len(jc)}/{len(man['judges'])} — {sorted(jc)}")
    add(any(e["kind"] == "RUN_COMPLETE" for e in evts),
        "L5.journal.run_complete")
    add(any(e["kind"] == "EXPORT" for e in evts), "L5.journal.export")
    add(not partial, "L5.journal.dernière_ligne",
        "incomplète (crash au moment de l'écriture)" if partial else "intègre")

    # --- L6 : export final, hash stable ------------------------------------
    zf = root / "final" / "m3b_adapters_final.zip"
    az = (man.get("artifacts") or {}).get("final_zip")
    if zf.is_file() and az:
        h = sha256_file(zf)
        add(h == az["sha256"], "L6.export_final.sha256",
            f"{h[:12]}… vs {az['sha256'][:12]}… "
            f"({zf.stat().st_size / 1e6:.0f} Mo)")
    else:
        add(False, "L6.export_final.présent", zf)

    # --- L7 : scellé M4 intact dans le dépôt de référence ------------------
    seal = seal_check_from_repo(repo)
    add(seal.get("ok") is True, "L7.scellé_m4.intègre",
        f"50 affaires, hash {'match' if seal.get('ok') else 'DIVERGENT'}")

    # --- L8 : rapport dérivé == manifeste ----------------------------------
    rp = root / "m3b_report.json"
    if rp.is_file() and st is not None:
        rep = json.load(open(rp, encoding="utf-8"))
        add(rep.get("results") == st.get("results"),
            "L8.rapport_dérivé.cohérent",
            f"{len(rep.get('results') or [])} lignes de résultats")

    ok_all = all(ok for ok, _, _ in links)
    return links, ok_all
