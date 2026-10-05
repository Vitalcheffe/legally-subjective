#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Outils Kaggle pour la mission M3b (LS-17) — push / poll / pull.

SÉCURITÉ (mandat §7) : le token est lu de /home/z/my-project/.kaggle_token,
n'est JAMAIS imprimé, loggé, écrit dans un kernel ou committé. Les fonctions
ci-dessous ne retournent que des faits dérivés.

Usage :
  python kaggle_tools.py push   <slug-court> <source.py> [--gpu NvidiaL4] [--internet] [--model SRC ...] [--data SRC ...] [--docker SHA] [--type script|notebook]
  python kaggle_tools.py poll   <slug-court>            # statut de la dernière session
  python kaggle_tools.py pull   <slug-court> [DEST]     # télécharge la sortie de la dernière version
  python kaggle_tools.py quota                          # quota accélérateurs
"""

import argparse
import io
import json
import os
import sys
import time
import zipfile

TOKEN_PATH = "/home/z/my-project/.kaggle_token"
OWNER = "aminehrc"                    # dérivé des kernels existants (audit)


def client():
    from kagglesdk.kaggle_client import KaggleClient
    token = open(TOKEN_PATH).read().strip()
    return KaggleClient(api_token=token), token


def bearer_get(token, path, params=None):
    import urllib.request, urllib.parse
    url = "https://www.kaggle.com/api/v1/" + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def do_push(args):
    from kagglesdk.kernels.types.kernels_api_service import ApiSaveKernelRequest
    cl, token = client()
    slug_full = f"{OWNER}/{args.slug}"
    text = open(args.source).read()

    # paramètres de session OPÉRATIONNELS seulement (budget temps, juges
    # par worker, kill de test) — jamais de secrets, jamais de science :
    # la science vit dans le dépôt épinglé que le runner exécute.
    if args.runner_args:
        header = (
            "# --- PARAMÈTRES DE SESSION (générés au push par kaggle_tools ;\n"
            "#     opérationnel uniquement — infrastructure, hors protocole) ---\n"
            "# GARDE : ne PAS écraser l'argv d'un worker — le runner se\n"
            "# ré-invoque en sous-processus avec --worker N ; l'en-tête ne\n"
            "# s'applique qu'au lancement initial du noyau (bug v3 du smoke :\n"
            "# l'en-tête réécrivait l'argv du sous-processus → boucle\n"
            "# parent→worker infinie jusqu'au tueur du noyau).\n"
            "import sys as _sys\n"
            "if '--worker' not in _sys.argv:\n"
            f"    _sys.argv = {_sys_argv(args.runner_args)}\n\n")
        text = header + text

    req = ApiSaveKernelRequest()
    req.slug = slug_full
    req.new_title = args.title or args.slug.replace("-", " ")
    req.text = text
    req.language = "python"
    req.kernel_type = args.type
    req.is_private = True                      # JAMAIS public (mandat §33)
    req.enable_gpu = bool(args.gpu)
    req.enable_tpu = False
    req.enable_internet = bool(args.internet)
    req.category_ids = ["gpu"] if args.gpu else []
    req.kernel_data_sources = args.data or []
    req.competition_data_sources = []
    req.model_data_sources = args.model or []
    if args.gpu:
        req.machine_shape = args.gpu
    if args.docker:
        req.docker_image = args.docker

    body = req.to_dict()
    body["text"] = (f"<{len(text)} caractères de source"
                    + (f" + argv {args.runner_args!r}>" if args.runner_args
                       else ">"))
    print("push:", json.dumps(body, indent=1))
    if args.dry:
        print("DRY RUN (—go pour pousser)")
        return 0
    resp = cl.kernels.kernels_api_client.save_kernel(req)
    d = resp.to_dict() if hasattr(resp, "to_dict") else vars(resp)
    print("PUSHED:", json.dumps(d, indent=1, default=str))
    return 0


def _sys_argv(raw):
    """Construit la liste argv depuis une chaîne façon shell."""
    import shlex
    return repr(["m3b_kaggle_runner"] + shlex.split(raw))


def do_poll(args):
    cl, token = client()
    deadline = time.time() + args.timeout
    last = None
    while time.time() < deadline:
        try:
            d = bearer_get(token, "kernels/status",
                           {"user_name": OWNER, "kernel_slug": args.slug})
        except Exception as e:
            print(f"[poll] {type(e).__name__}: {str(e)[:120]}")
            time.sleep(20)
            continue
        status = d.get("status")
        if status != last:
            print(f"[{time.strftime('%H:%M:%S')}] status = {status}"
                  + (f" | failure: {str(d.get('failureMessage'))[:200]}" if d.get("failureMessage") else ""))
            last = status
        if status in ("complete", "error", "cancelAcknowledged", "cancelled"):
            print("final:", json.dumps(d, indent=1, default=str))
            return 0 if status == "complete" else 1
        time.sleep(args.every)
    print(" TIMEOUT du poll")
    return 2


def do_pull(args):
    cl, token = client()
    dest = args.dest or f"/home/z/my-project/kout/{args.slug}"
    os.makedirs(dest, exist_ok=True)
    d = bearer_get(token, "kernels/output",
                   {"user_name": OWNER, "kernel_slug": args.slug})
    files = d.get("files", [])
    print(f"{len(files)} fichiers en sortie :")
    import urllib.request
    got = []
    for f in files:
        name = f.get("fileName") or ""
        url = f.get("url")
        if not url:
            continue
        out = os.path.join(dest, name.replace("/", "_"))
        try:
            urllib.request.urlretrieve(url, out)
            print(f"  {name} ({os.path.getsize(out)} octets) → {out}")
            got.append(out)
        except Exception as e:
            print(f"  {name} ÉCHEC {e}")
    # log complet de la session si présent
    for f in files:
        if f.get("fileName") == f"{args.slug}.log":
            print("log de session disponible :", f.get("url"))
    return 0 if got else 1


def do_quota(_args):
    cl, token = client()
    from kagglesdk.kernels.types.kernels_api_service import (
        ApiGetAcceleratorQuotaStatisticsRequest)
    qreq = ApiGetAcceleratorQuotaStatisticsRequest()
    qresp = cl.kernels.kernels_api_client.get_accelerator_quota_statistics(qreq)
    print(json.dumps(qresp.to_dict(), indent=1, default=str))
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("push")
    p.add_argument("slug")
    p.add_argument("source")
    p.add_argument("--title")
    p.add_argument("--gpu", default=None)
    p.add_argument("--internet", action="store_true")
    p.add_argument("--model", action="append")
    p.add_argument("--data", action="append")
    p.add_argument("--docker")
    p.add_argument("--type", default="script", choices=["script", "notebook"])
    p.add_argument("--runner-args", default=None,
                   help="argv opérationnel du runner (soft-minutes, juges, "
                        "kill de test) — préfixé au source au push")
    p.add_argument("--dry", action="store_true")
    p.set_defaults(fn=do_push)

    p = sub.add_parser("poll")
    p.add_argument("slug")
    p.add_argument("--timeout", type=float, default=3600)
    p.add_argument("--every", type=float, default=20)
    p.set_defaults(fn=do_poll)

    p = sub.add_parser("pull")
    p.add_argument("slug")
    p.add_argument("dest", nargs="?")
    p.set_defaults(fn=do_pull)

    p = sub.add_parser("quota")
    p.set_defaults(fn=do_quota)

    args = ap.parse_args()
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()
