#! /usr/bin/env python3

import json
import os
import sys
from typing import Dict, List, Set, Tuple

import requests
import time
from libcordra import Cordra


QUERY_TERM = "materials"
TOP_LEVEL_ID = "300010358"
AAT_BASE_URL = "https://vocab.getty.edu/aat/"
HDL_PREFIX = "21.11158/"
HDL_SHOULDER = "vocab:aat:"

ERIHS_API_URL = "https://vocab.e-rihs.io/opentheso2/openapi/v1/concept/th1/"

CORDRA_API_URL = "https://data.e-rihs.io/"
CORDRA_TYPE = "VocabularyConcept"


def aat_json_url(aat_id: str) -> str:
    return f"{AAT_BASE_URL}{aat_id}.json"


def handle_for_aat_id(aat_id: str) -> str:
    return f"{HDL_PREFIX}{HDL_SHOULDER}{aat_id}"


def extract_aat_id(uri: str) -> str:
    if not uri:
        return ""
    uri = uri.rstrip("/")
    return uri.split("/")[-1]


def extract_language_code(language_list: List[dict]) -> str:
    if not language_list:
        return ""
    lang_obj = language_list[0] or {}
    # Prefer explicit label if present, else parse code from URI
    if "_label" in lang_obj and lang_obj["_label"]:
        return str(lang_obj["_label"])
    lang_id = lang_obj.get("id", "")
    return extract_aat_id(lang_id)


def fetch_aat_concept(aat_id: str) -> dict:
    url = aat_json_url(aat_id)
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()


def normalize_uri(uri: str) -> str:
    if not uri:
        return ""
    u = uri.strip().rstrip("/")
    if u.startswith("https://"):
        u = "http://" + u[len("https://") :]
    return u


def find_erihs_exact_matches(pref_label: str, expected_aat_uri: str) -> List[str]:
    if not pref_label:
        return []
    params = {"q": pref_label, "match": "exact"}
    headers = {"accept": "application/json;charset=utf-8"}
    try:
        resp = requests.get(ERIHS_API_URL + "search", params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json() or {}
    except Exception:
        return []

    expected_norm = normalize_uri(expected_aat_uri)
    matches: List[str] = []
    for handle_uri, erihs_concept in (data.items() if isinstance(data, dict) else []):
        exact_list = erihs_concept.get("http://www.w3.org/2004/02/skos/core#exactMatch", []) or []
        for item in exact_list:
            value_uri = normalize_uri(item.get("value", ""))
            if value_uri and value_uri == expected_norm:
                matches.append(handle_uri)
                break
    return matches


def transform_concept(concept: dict, aat_id: str) -> dict:
    # prefLabel
    pref_label = concept.get("_label") or ""

    # terms from identified_by (preferred and alternatives)
    terms: List[dict] = []
    seen_terms: Set[Tuple[str, str, bool]] = set()
    for ident in concept.get("identified_by", []) or []:
        label = (ident.get("content") or "").strip()
        lang = extract_language_code(ident.get("language", []) or [])
        if label:
            key = (label, lang, False)
            if key not in seen_terms:
                terms.append({"label": label, "lang": lang, "isAlternative": False})
                seen_terms.add(key)
        for alt in ident.get("alternative", []) or []:
            alt_label = (alt.get("content") or "").strip()
            alt_lang = extract_language_code(alt.get("language", []) or [])
            if alt_label:
                key_alt = (alt_label, alt_lang, True)
                if key_alt not in seen_terms:
                    terms.append({"label": alt_label, "lang": alt_lang, "isAlternative": True})
                    seen_terms.add(key_alt)

    # descriptions from subject_of
    descriptions: List[dict] = []
    for subj in concept.get("subject_of", []) or []:
        content = (subj.get("content") or "").strip()
        if not content:
            continue
        lang = extract_language_code(subj.get("language", []) or [])
        descriptions.append({"description": content, "lang": lang})

    # broader handles (skip for top-level)
    broader_handles: List[str] = []
    if aat_id != TOP_LEVEL_ID:
        for broader in concept.get("broader", []) or []:
            broader_uri = broader.get("id") or ""
            broader_id = extract_aat_id(broader_uri)
            if broader_id:
                broader_handles.append(handle_for_aat_id(broader_id))

    # exactMatch to AAT concept (non-JSON URL)
    exact_match_uri = concept.get("id") or f"{AAT_BASE_URL}{aat_id}"
    exact_match = [
        {"uri": exact_match_uri, "scheme": "AAT", "primarySource": True}
    ]

    result: Dict[str, object] = {
        "id": handle_for_aat_id(aat_id),
        "prefLabel": pref_label,
        "terms": terms,
        "descriptions": descriptions,
        "broader": broader_handles,
        "narrower": [],
        "exactMatch": exact_match,
    }

    if aat_id == TOP_LEVEL_ID:
        result["queryTerms"] = [QUERY_TERM, "TOP_LEVEL"]

    return result


def load_env_files() -> None:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    for base in (root_dir, script_dir):
        env_path = os.path.join(base, ".env")
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            key, val = line.split("=", 1)
                            key = key.strip()
                            val = val.strip().strip('"').strip("'")
                            if key and key not in os.environ:
                                os.environ[key] = val
            except Exception:
                pass


def upload_to_cordra(cordra: Cordra, obj: dict) -> bool:
    digital_object = {
        "id": obj.get("id"),
        "type": CORDRA_TYPE,
        "content": obj,
    }
    try:
        cordra.batch_upload([digital_object])
        return True
    except SystemExit:
        return False
    except Exception:
        return False


def collect_narrower_ids(concept: dict) -> List[str]:
    ids: List[str] = []
    for item in concept.get("narrower", []) or []:
        uri = item.get("id") or ""
        child_id = extract_aat_id(uri)
        if child_id:
            ids.append(child_id)
    return ids


def main() -> None:
    load_env_files()
    cordra_user = os.getenv("CORDRA_USER")
    cordra_passwd = os.getenv("CORDRA_PASSWD")
    if not cordra_user or not cordra_passwd:
        print("\033[91mMissing CORDRA_USER or CORDRA_PASSWD in environment/.env\033[0m")
        sys.exit(1)

    cordra = Cordra(CORDRA_API_URL, cordra_user, cordra_passwd)

    work_list: List[str] = [TOP_LEVEL_ID]
    processed: Set[str] = set()

    # progress
    print(f"Starting traversal from AAT {TOP_LEVEL_ID} -> {handle_for_aat_id(TOP_LEVEL_ID)}")
    start_time = time.time()

    try:
        while work_list:
            current_id = work_list.pop(0)
            if current_id in processed:
                continue

            concept = fetch_aat_concept(current_id)
            transformed = transform_concept(concept, current_id)

            # try to enrich with E-RIHS exactMatch
            expected_aat_uri = concept.get("id") or f"{AAT_BASE_URL}{current_id}"
            erihs_handles = find_erihs_exact_matches(transformed.get("prefLabel", ""), expected_aat_uri)
            if erihs_handles:
                existing_uris = {em.get("uri") for em in transformed.get("exactMatch", [])}
                for h in erihs_handles:
                    if h not in existing_uris:
                        transformed.setdefault("exactMatch", []).append(
                            {"uri": h, "scheme": "E-RIHS", "primarySource": False}
                        )

            child_ids = collect_narrower_ids(concept)
            erihs_status = "yes" if erihs_handles else "no"
            print(
                f"[AAT {current_id}] {transformed['id']} | prefLabel: "
                f"{transformed.get('prefLabel', '')} | narrower: {len(child_ids)} | "
                f"E-RIHS match: {erihs_status}"
            )

            success = upload_to_cordra(cordra, transformed)
            if success:
                print(f"\033[92muploaded to Cordra: {transformed['id']}\033[0m")
            else:
                print(f"\033[91mfailed to upload to Cordra: {transformed['id']}\033[0m")

            # queue narrower concepts for later processing
            for child_id in child_ids:
                if child_id not in processed and child_id not in work_list:
                    work_list.append(child_id)

            processed.add(current_id)
            print(f"work list length: {len(work_list)}")
    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        print(f"Interrupted. Concepts processed: {len(processed)} | time: {elapsed:.2f}s")
        return

    # finished
    elapsed = time.time() - start_time
    print(f"Finished. Concepts processed: {len(processed)} | time: {elapsed:.2f}s")


if __name__ == "__main__":
    main()
