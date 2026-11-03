"""Phase 10 (0.10.0): six interface languages (I18N-1), the terminology base (TERM-1), cross-language search (XSEARCH-1), the
translation quality observatory (I18N-Q1), multilingual reports, the signal workbench (SIGNAL-1, known answers), the signature
systems (WORLD-1, CONV-1, LEAD-1, NEGX-1, MODAL-1, OPP-2, KCOMP-1, EXTSRC-1, AGENTS-1, EXPLAIN-1, TIMES-1, DIRECT-1, EXPMKT-1) and
the handoff protocol (HANDOFF-1), with browser parity for translation, search and handoffs."""

import importlib.util
import json
import re
import shutil
import subprocess
import unicodedata
from functools import lru_cache
from pathlib import Path

import numpy as np
import pytest

from skytrace import analysis, bundle as bmod, canon, handoff, i18n, sigintel, universal, xsearch
from skytrace.report import Event, Investigation, render_markdown

ROOT = Path(__file__).resolve().parents[2]
I18N = ROOT / "web" / "i18n"
LANGS = ["bn", "hi", "es", "fr", "de"]
NODE = shutil.which("node")
NATIVE = {"bn": ("ঀ", "৿"), "hi": ("ऀ", "ॿ")}


def _script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@lru_cache(maxsize=None)
def _rec(tid):
    return json.loads(json.dumps(analysis.run(bmod.load(bmod.SYNTHETIC_ROOT / tid)).to_dict()))


@lru_cache(maxsize=None)
def _ctx(tid):
    """The inputs the server passes to universal.report, built with the same modules the server uses."""
    from skytrace import compat, discovery, epistemic as epi, hypotheses, ledger, negspace, quality, radar, scicomp
    from skytrace.view import InvestigationView, evidence_graph
    rec = _rec(tid)
    b = bmod.load(bmod.SYNTHETIC_ROOT / tid)
    v = InvestigationView(rec, b.discovery, b.manifest, b.inspection)
    disc = discovery.report(rec, b.discovery, b.manifest, {})
    L = ledger.build(rec, evidence_graph(v, tid), b.discovery)
    Q = quality.checks(rec, b.manifest, b.discovery, b.path)
    G = epi.build(rec, disc, L, b.manifest)
    comp = scicomp.compile_investigation(rec, G, disc, L, b.manifest, Q)
    rad = radar.scan(rec, compat.report(rec, b.discovery, b.manifest), Q, L, hypotheses.evaluate(rec), network=False)
    return rec, disc, {"negative": negspace.registry(rec, disc, L), "compile": comp}, rad


def _catalog():
    return {m["k"]: m["s"] for m in json.loads((I18N / "catalog.json").read_text(encoding="utf-8"))["messages"]}


# ------------------------------------------------------------------ I18N-1: completeness and validation
def test_every_message_is_translated_in_every_language_with_identical_placeholders():
    src = _catalog()
    keys = json.loads((I18N / "en.json").read_text(encoding="utf-8"))["keys"]
    assert len(src) > 3000
    for lang in LANGS:
        d = json.loads((I18N / f"{lang}.json").read_text(encoding="utf-8"))
        assert d["status"] == "machine-translated by an AI model; not reviewed by a native speaker" and d["reviewed"] is False
        assert d["version"] == "0.10.0"
        missing = [k for k in src if not d["messages"].get(k)]
        assert missing == [], f"{lang}: {len(missing)} untranslated, e.g. {[src[k] for k in missing[:3]]}"
        assert set(keys) <= set(d["keys"])
        for k, en in src.items():
            tr = d["messages"][k]
            assert sorted(re.findall(r"\{[0-9a-z_]+\}", tr)) == sorted(re.findall(r"\{[0-9a-z_]+\}", en)), (lang, en)
            assert "�" not in tr and unicodedata.normalize("NFC", tr) == tr, (lang, tr)
        for k, en in keys.items():
            tr = d["keys"][k]
            if isinstance(en, dict):
                assert isinstance(tr, dict) and "other" in tr and all("{n}" in v for v in tr.values())
            else:
                assert sorted(re.findall(r"\{\w+\}", tr)) == sorted(re.findall(r"\{\w+\}", en))


def test_translations_keep_numbers_and_method_identifiers():
    src = _catalog()
    num = re.compile(r"\d+(?:\.\d+)?")
    for lang in LANGS:
        msgs = json.loads((I18N / f"{lang}.json").read_text(encoding="utf-8"))["messages"]
        for k, en in src.items():
            tr = re.sub(r"\{\d+\}", "", msgs[k])
            for n in num.findall(re.sub(r"\{\d+\}", "", en)):
                assert n in tr or n.replace(".", ",") in tr, (lang, en, msgs[k])
            for ident in i18n.IDS.findall(en):
                assert ident in msgs[k], (lang, ident, msgs[k])


def test_bangla_and_hindi_translations_use_their_own_scripts():
    src = _catalog()
    for lang, (lo, hi) in NATIVE.items():
        msgs = json.loads((I18N / f"{lang}.json").read_text(encoding="utf-8"))["messages"]
        prose = lambda en: re.sub(r"\S*[./_]\S*|\{\d+\}", "", en)        # file names, paths and identifiers are not prose  # noqa: E731
        worded = [k for k, en in src.items() if len(re.findall(r"[A-Za-z]{4,}", prose(en))) >= 3 and msgs[k] != en]
        native = [k for k in worded if any(lo <= c <= hi for c in msgs[k])]
        assert len(native) == len(worded), [msgs[k] for k in set(worded) - set(native)][:5]


def test_generated_i18n_files_are_up_to_date():
    for name, out in (("i18n_extract", "source.json up to date"), ("i18n_terms", "terms.json up to date"), ("i18n_quality", "quality.json up to date")):
        r = subprocess.run(["python", str(ROOT / "scripts" / f"{name}.py"), "--check"], capture_output=True, text=True, cwd=ROOT)
        assert r.returncode == 0 and out in r.stdout, (name, r.stdout, r.stderr)


def test_quality_observatory_counts_and_terminology_consistency():
    q = i18n.quality()
    assert q["method"] == "I18N-Q1" and q["n_messages"] > 3000 and q["n_terms"] >= 48
    for lang, v in q["languages"].items():
        assert v["translated"] == q["n_messages"] and v["n_missing"] == 0
        assert not v["placeholder_mismatches"] and not v["unicode_problems"] and not v["not_nfc"]
        assert not v["numbers_changed"] and not v["identifiers_changed"]
        assert v["terminology"]["inconsistent"] == 0 and v["terminology"]["consistent"] > 500
        assert v["reviewed"] is False and "machine-translated" in v["status"]
    assert "%" not in json.dumps({k: v["expansion"] for k, v in q["languages"].items()})


def test_terminology_base_covers_six_languages_with_definitions_and_pronunciation():
    t = json.loads((I18N / "terms.json").read_text(encoding="utf-8"))
    assert t["method"] == "TERM-1" and t["n"] >= 48 and "not reviewed" in t["status"]
    ids = [x["id"] for x in t["terms"]]
    assert len(ids) == len(set(ids))
    for x in t["terms"]:
        assert x["en"]["term"] and len(x["en"]["definition"]) > 30
        for lang in LANGS:
            assert x[lang]["term"] and x[lang]["definition"] and x[lang]["match"], (x["id"], lang)
            for u in re.findall(r"µm|µJy|mas|σ|χ²|AIC|BIC|WLMATCH-2|SHA-256", x["en"]["definition"]):
                assert u in x[lang]["definition"], (x["id"], lang, u)
        assert x["bn"]["pronunciation"] and x["hi"]["pronunciation"]


# ------------------------------------------------------------------ multilingual reports
def test_report_in_six_languages_keeps_every_number_and_engine_statement():
    rec = _rec("syn-var-1")
    inv = Investigation(rec["target"], rec["parameters"])
    inv.events = [Event(**{k: ev[k] for k in ("step", "status", "detail", "data", "provenance")}) for ev in rec["events"]]
    inv.created_at = rec["created_at"]
    en = render_markdown(inv)
    assert en == render_markdown(inv, "en") and not en.startswith("<!--")
    outcomes = next(e for e in rec["events"] if e["step"] == "assess")["data"]["outcomes"]
    for lang in LANGS:
        t = render_markdown(inv, lang)
        assert t.startswith(f"<!-- language: {i18n.LANGS[lang][0]} ({lang}); interface translation: machine-translated by an AI model")
        lines = [ln for ln in t.splitlines()[2:] if not (ln.startswith("> ") and f"({lang})" in ln)]
        assert sorted(i18n.numbers("\n".join(lines))) == sorted(i18n.numbers(en))
        for o in outcomes:
            assert o["statement"] in t                              # engine statements are not translated
        assert "```json" in t and json.dumps(rec["parameters"], indent=2, sort_keys=True) in t
        assert "SYNTHETIC" in t or "সিনথেটিক" in t or "কৃত্রিম" in t or "कृत्रिम" in t
    assert render_markdown(inv, "xx") == en


def test_server_translation_matches_marked_messages():
    assert i18n._t("Investigation: {0}", "de", "SYN-VAR-1") == "Untersuchung: SYN-VAR-1"
    assert i18n._t("Rejected or failed ({0})", "fr", 3) == "Rejetés ou échoués (3)"
    assert i18n._t("not a catalogue message {0}", "bn", 1) == "not a catalogue message 1"
    assert i18n.translate_text("Run analysis", "es") is not None and i18n.translate_text("Run analysis", "en") is None
    # a pattern made of one connective ("{0} of {1}") translates counts, never part of a recorded English sentence
    assert i18n.translate_text("3666 of 3666", "de") == "3666 von 3666"
    for lang in LANGS:
        assert i18n.translate_text("46 of 48 exposures are usable.", lang) is None
        assert i18n.translate_text("alpha and beta", lang) is None


# ------------------------------------------------------------------ XSEARCH-1
def test_cross_language_search_maps_terms_and_never_claims_semantics():
    T = json.loads((I18N / "terms.json").read_text(encoding="utf-8"))
    for q, term in [("নিজস্ব গতি", "proper motion"), ("लंबन", "parallax"), ("movimiento propio", "proper motion"), ("étalonnage", "calibration"),
                    ("Eigenbewegung", "proper motion"), ("Wellenlängen", "wavelength"), ("PERIODOGRAMA", "periodogram")]:
        e = xsearch.expand(q, T)
        assert term in e["english"], (q, e)
    assert xsearch.expand("নিজস্ব গতি", T)["script"] == "bn" and xsearch.expand("लंबन", T)["script"] == "hi"
    docs = [{"id": "a", "text": "Proper motion fit (LINFIT-LOO-1)"}, {"id": "b", "text": "Reference-calibrated pairs"}, {"id": "c", "text": "Parallax"}]
    r = xsearch.search("নিজস্ব গতি", docs, T, "bn")
    assert [x["id"] for x in r["results"]] == ["a"] and r["results"][0]["layer"] == 2
    assert "not semantic search" in r["label"]
    assert xsearch.search("zzzz qqqq", docs, T)["results"] == []
    assert xsearch.normalize("Étalonnage  ÉCHANTILLONNÉ") == "etalonnage echantillonne"


# ------------------------------------------------------------------ SIGNAL-1 known answers
def test_signal_methods_known_answers():
    rng = np.random.default_rng(7)
    t = np.sort(rng.uniform(0, 300, 60))
    y = 5 + 1.5 * np.sin(2 * np.pi * t / 23.0) + rng.normal(0, 0.2, 60)
    dy = np.full(60, 0.2)
    a = sigintel.analyse({"t": t.tolist(), "y": y.tolist(), "dy": dy.tolist(), "unit": "u"})
    assert abs(a["lomb_scargle"]["peak"]["period"] - 23.0) < 0.5 and a["lomb_scargle"]["periodicity_candidate"]
    assert {s["method"]: s["applicable"] for s in a["selection"]}["fourier"] is False          # uneven sampling
    # Theil–Sen is unaffected by one wild point; least squares is pulled
    tt = np.arange(20.0)
    yy = 2.0 * tt + 1
    yy[5] = 500.0
    ts = sigintel.theil_sen(tt, yy)
    assert abs(ts["slope"] - 2.0) < 1e-9 and abs(sigintel.wls_line(tt, yy, np.ones(20))["slope"] - 2.0) > 0.5
    # one step between index 9 and 10
    ys = np.r_[np.full(10, 1.0), np.full(10, 4.0)] + rng.normal(0, 0.05, 20)
    cp = sigintel.change_point(tt, ys, np.full(20, 0.05))
    assert cp["index"] == 10 and abs(cp["mean_after"] - cp["mean_before"] - 3.0) < 0.1
    # DCF of a densely sampled sinusoid: positive at short lags, negative near half a period
    t2 = np.linspace(0, 100, 101)
    y2 = np.sin(2 * np.pi * t2 / 40.0)
    d = sigintel.dcf(t2, y2, np.full(101, 0.01), n_bins=10)
    assert d["bins"][0]["dcf"] > 0.5 and min(b["dcf"] for b in d["bins"][1:4]) < -0.5
    # the window of uniform sampling peaks at multiples of the sampling frequency only
    w = sigintel.window(np.arange(48.0), np.array([0.0, 0.25, 1.0]))      # 48 = whole cycles of the 0.25 frequency
    assert abs(w[0] - 1) < 1e-12 and w[1] < 1e-6 and abs(w[2] - 1) < 1e-9
    # uniform series: Fourier and wavelet apply and find the right frequency
    yu = np.sin(2 * np.pi * np.arange(64) / 8.0)
    au = sigintel.analyse({"t": list(range(64)), "y": yu.tolist(), "dy": [0.1] * 64, "unit": "u"})
    assert au["sampling"]["uniform"] and abs(au["fourier"]["peak_frequency"] - 0.125) < 1e-9 and au["wavelet"]["used"] == 64
    # too few points: methods refuse with a reason instead of running
    a4 = sigintel.analyse({"t": [0, 1, 2, 3], "y": [1, 2, 1, 2], "dy": [1] * 4, "unit": "u"})
    sel = {s["method"]: s for s in a4["selection"]}
    assert not sel["lomb_scargle"]["applicable"] and "< 12" in sel["lomb_scargle"]["reason"] and "lomb_scargle" not in a4


def test_bic_only_when_assumptions_hold():
    rng = np.random.default_rng(3)
    t = np.linspace(0, 10, 40)
    y = 0.8 * t + rng.normal(0, 0.5, 40)
    mc = sigintel.model_comparison(t, y, np.full(40, 0.5))
    assert mc["bic_reported"]
    bic = {m["model"]: m["bic"] for m in mc["models"]}
    assert bic["linear trend"] < bic["constant"]
    mc2 = sigintel.model_comparison(t, y, np.full(40, 0.05))           # errors understated tenfold: χ²ν ≫ 2
    assert not mc2["bic_reported"] and all(m["bic"] is None for m in mc2["models"]) and "not reported" in mc2["reading"]


def test_signal_workbench_on_a_record_never_interpolates():
    w = sigintel.workbench(_rec("syn-var-1"))
    assert w["method"] == "SIGNAL-1" and w["series"]
    rec = _rec("syn-var-1")
    measured = {round(e["data"]["mjd"], 6) for e in rec["events"] if e["step"] == "measure"}
    for s in w["series"]:
        if s["unit"] == "µJy":
            assert {round(x, 6) for x in s["data"]["t"]} <= measured
            assert s["lambda_spread_um"] <= s["tolerance_um"]
        assert all(x["reason"] for x in s["analysis"]["selection"])


# ------------------------------------------------------------------ the signature systems
def _uni(tid="syn-var-1"):
    rec, disc, rep, rad = _ctx(tid)
    return universal.report(rec, disc["hypotheses"], (rep or {}).get("negative"), (rep or {}).get("compile"), rad, False,
                            [rec["content_hash"], "0" * 64], set())


def test_convergence_groups_shared_exposures_and_never_counts_repeated_data():
    rec = {"events": [{"step": "variability", "status": "ok", "data": {"pairs": [
        {"a": "A", "b": "B", "z": 9, "differential": {"calibrated": True, "z_cal": 9, "ref_ids": ["r1", "r2"]}},
        {"a": "B", "b": "C", "z": 8, "differential": {"calibrated": True, "z_cal": 8, "ref_ids": ["r1"]}},
        {"a": "D", "b": "E", "z": 7, "differential": {"calibrated": True, "z_cal": 7, "ref_ids": ["r1", "r3"]}},
        {"a": "F", "b": "G", "z": 9, "differential": {"calibrated": True, "z_cal": 2, "ref_ids": ["r4"]}}]}}], "content_hash": "x"}
    c = universal.convergence(rec, ["x", "y", "z"])
    v = c["outcomes"][0]
    assert v["lines"] == 3 and v["independent_by_exposure"] == 2 and v["shared_reference_stars"] == ["r1"]
    assert c["repeated_data"]["sibling_runs"] == 2 and "not independent confirmation" in c["repeated_data"]["reading"]
    ld = universal.leads(rec)
    assert [l["kind"] for l in ld["leads"]] == ["method disagreement"] and ld["leads"][0]["status"] == "research lead"
    assert "not a paradox" in ld["note"]


def test_negative_space_nine_distinctions_say_what_they_do_not_mean():
    u = _uni("syn-var-1")
    n = u["negative"]
    assert n["distinctions"] == universal.DISTINCTIONS and len(n["distinctions"]) == 9
    assert n["counts"]["measured absence"] >= 1                     # motion: no motion at the stated sensitivity
    assert n["counts"]["unknown quantity"] >= 1 and n["counts"]["unavailable dataset"] >= 1
    for x in n["items"]:
        assert x["does_not_mean"] == universal.DOES_NOT_MEAN[x["distinction"]]
    assert "not proof" in universal.DOES_NOT_MEAN["non-detection"] and "not proof" in universal.DOES_NOT_MEAN["measured absence"]


def test_world_model_relationships_have_a_basis_and_queries_are_exact():
    u = _uni("syn-var-1")
    w = u["world"]
    assert all(e["basis"]["rule"] and e["basis"]["field"] for e in w["edges"])
    hyp = universal.world_query(w, {"from_kind": "hypothesis"})
    assert hyp and all(e["from"].startswith("hypothesis:") for e in hyp)
    assert universal.world_query(w, {"rel": "compared with", "text": "zzz-not-there"}) == []
    assert {"consistent so far with", "contradicted by"} & set(w["relations"])


def test_opportunities_sources_compiler_agents_director_and_market_stay_honest():
    u = _uni("syn-var-1")
    o = u["opportunities"]
    assert o["items"] and all(len(o["fields"]) == 10 for _ in [0])
    for i in o["items"]:
        assert i["novelty"]["scope"] in ("new to this investigation", "new to this collection")
        assert i["novelty"]["underexplored_in_indexed_sources"].startswith("not evaluated") and i["novelty"]["independently_verified"].startswith("not evaluated")
    assert "globally novel" in o["note"] and "never" in o["note"]
    assert all(s["state"] == "not connected" and s["updates"] == [] for s in u["sources"]["sources"])
    assert {s["status"] for s in u["compiler"]["stages"]} <= set(universal.COMPILER_STATUSES)
    assert "does not prove" in u["compiler"]["meaning"]
    assert universal.compiler_statuses({"stages": [{"id": "x", "counts": {"pass": 0, "warning": 0, "fail": 0}}]})["stages"][0]["status"] == "Not evaluated"
    assert universal.compiler_statuses({"stages": [{"id": "x", "counts": {"pass": 3, "warning": 0, "fail": 1}}]})["stages"][0]["status"] == "Failed"
    assert "not independent confirmation" in u["agents"]["caveat"] and len(u["agents"]["roles"]) == 5
    assert all(m["cites"] for r in u["agents"]["rounds"] for m in r["messages"])
    assert all(s["requires_approval"] for s in u["director"]["steps"]) and u["director"]["steps"][-1]["workspace"] == "gateway"
    for m in u["market"]["items"]:
        assert m["recommended"] == (m["evidence"] is not None)
        if m["evidence"]:
            f, fn = m["evidence"].split("::")
            assert (ROOT / f).exists() and f"def {fn}(" in (ROOT / f).read_text()


def test_explanations_use_keyed_messages_present_in_every_language():
    u = _uni("syn-hpm-1")
    keys = json.loads((I18N / "en.json").read_text(encoding="utf-8"))["keys"]
    langs = {lang: json.loads((I18N / f"{lang}.json").read_text(encoding="utf-8"))["keys"] for lang in LANGS}
    assert [L["layer"] for L in u["explain"]["outcomes"][0]["layers"]] == universal.LAYERS
    for o in u["explain"]["outcomes"]:
        for L in o["layers"]:
            assert L["key"] in keys and all(L["key"] in d for d in langs.values())
            assert set(re.findall(r"\{(\w+)\}", keys[L["key"]])) <= set(L["params"])


def test_timeline_keeps_four_kinds_of_time_apart():
    tl = universal.timeline(_rec("syn-var-1"))
    assert [x["lane"] for x in tl["lanes"]] == ["observation", "processing", "publication", "event"]
    assert tl["lanes"][3]["items"] == [] and "not determined" in tl["lanes"][3]["state"]
    assert all(i["time"].endswith("Z") for i in tl["lanes"][0]["items"])


def test_multimodal_rows_keep_units_and_compatibility_rules():
    m = universal.multimodal(_rec("syn-var-1"))
    assert m["counts"]["photometry"] > 0 and m["counts"]["astrometry"] > 0
    assert {r["unit"] for r in m["rows"] if r["modality"] == "photometry"} == {"µJy"}
    assert any("never compared" in r["compatible"] for r in m["compatibility"])


# ------------------------------------------------------------------ HANDOFF-1
def test_handoff_round_trip_and_validation():
    u = _uni("syn-var-1")
    rec = _rec("syn-var-1")
    h = handoff.build(rec, u, "bn", i18n.meta("bn"), "2026-11-03T10:00:00+00:00", "0.10.0")
    assert handoff.validate(h) == []
    assert h["investigation"]["synthetic"] is True and h["language"] == {"interface": "bn", "content": "en", "translation": {
        "status": "machine-translated by an AI model; not reviewed by a native speaker", "translator": "Claude (Anthropic AI model), Skytrace Phase 10", "reviewed": False}}
    t = json.loads(json.dumps(h))
    t["established"][0]["category"] = "discovery"
    assert any("digest" in e for e in handoff.validate(t))
    t = json.loads(json.dumps(h))
    t["investigation"]["synthetic"] = False
    t["digest"] = canon.digest({k: v for k, v in t.items() if k != "digest"})
    assert any("labelled synthetic" in e for e in handoff.validate(t))
    assert handoff.validate({"schema": "other"}) == ["schema must be skytrace.handoff/1"]
    assert any("unknown version" in e for e in handoff.validate({**h, "version": "9.9"}))
    assert any("unknown field" in e for e in handoff.validate({**h, "extra": 1}))


# ------------------------------------------------------------------ browser parity
@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_browser_translation_search_and_handoff_match_python(tmp_path):
    src = _catalog()
    texts = [s for s in src.values() if not re.search(r"\d", s)][:400:7] + ["Investigation: SYN-VAR-1", "Rejected or failed (x)", "no such message",
                                                                                   "alpha and beta", "the edge of the field"]   # connective patterns: numbers only
    T = json.loads((I18N / "terms.json").read_text(encoding="utf-8"))
    queries = ["নিজস্ব গতি", "लंबन मापन", "movimiento propio de la estrella", "Eigenbewegung", "étalonnage", "Wellenlängen", "proper motion fit", "zzz"]
    docs = [{"id": "a", "text": "Proper motion fit (LINFIT-LOO-1)"}, {"id": "b", "text": "Reference-calibrated pairs: calibration"},
            {"id": "c", "text": "Parallax correction"}, {"id": "d", "text": "Wavelength-matched pairs"}]
    u = _uni("syn-var-1")
    rec = _rec("syn-var-1")
    meta = i18n.meta("fr")
    h = handoff.build(rec, u, "fr", meta, "2026-11-03T10:00:00+00:00", "0.10.0")
    bad = json.loads(json.dumps(h))
    bad["open"] = "x"
    tampered = json.loads(json.dumps(h))
    tampered["limitations"] = ["none"]
    job = {"langs": LANGS, "texts": texts, "keyed": [["explain.method", {"methods": "A, B"}], ["explain.result", {"category": "x"}]],
           "queries": queries, "docs": docs, "ui": "de", "record": rec, "universal": {k: u[k] for k in ("leads", "negative", "opportunities")},
           "hlang": "fr", "meta": meta, "created_at": "2026-11-03T10:00:00+00:00", "version": "0.10.0",
           "validate": [h, bad, tampered, {"schema": "skytrace.handoff/1", "version": "0"}, [1]]}
    p = tmp_path / "job.json"
    p.write_text(json.dumps(job))
    r = subprocess.run([NODE, str(ROOT / "tests/js/phase10_parity.mjs"), str(ROOT), str(p)], capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    js = json.loads(r.stdout)
    for lang in LANGS:
        assert js["translate"][lang] == [i18n.translate_text(s, lang) for s in texts], lang
        keyed = json.loads((I18N / f"{lang}.json").read_text(encoding="utf-8"))["keys"]
        assert js["keyed"][lang][0] == keyed["explain.method"].replace("{methods}", "A, B")
    assert js["normalize"] == [xsearch.normalize(q) for q in queries]
    assert js["expand"] == [xsearch.expand(q, T) for q in queries]
    assert js["search"] == [xsearch.search(q, docs, T, "de") for q in queries]
    assert js["handoff"] == h
    assert js["validate"] == [handoff.validate(d) for d in job["validate"]]
