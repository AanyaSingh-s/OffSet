"""Collect evaluation CSVs into reports/results.md (tables for the paper)."""
import pandas as pd

from OffSet.ml_service.offset_ml.config import reports_dir

NAMES = {"rules_only": "A. Rules only"}


def label(system: str) -> str:
    if system in NAMES:
        return NAMES[system]
    kind, model = system.split("_", 1)
    return ("B. ML only: " if kind == "ml" else "C. Hybrid: ") + model


def main() -> None:
    out = reports_dir()
    lines = ["# Results (held-out test users)", ""]
    cols = ["precision", "recall", "f1", "fpr", "fnr", "roc_auc", "pr_auc"]
    for tier in ("extended", "native"):
        t = pd.read_csv(out / f"overall_{tier}.csv")
        t.insert(0, "System", t.pop("system").map(label))
        lines += [f"## Overall, {tier} tier", "", t[["System"] + cols + ["tp", "fp", "fn", "tn"]].round(3).to_markdown(index=False), ""]
        ci = out / f"bootstrap_ci_{tier}.csv"
        if ci.exists():
            c = pd.read_csv(ci)
            c["system"] = c["system"].map(label)
            lines += [f"95% user-bootstrap intervals, {tier} tier", "", c.round(3).to_markdown(index=False), ""]
        r = pd.read_csv(out / f"residual_{tier}.csv")
        lines += [f"## ML on rule-passing rows only, {tier} tier", "", r.round(3).to_markdown(index=False), ""]
        s = pd.read_csv(out / f"scenario_{tier}.csv")
        keep = s[s.system.isin(["rules_only", "ml_random_forest", "hybrid_random_forest"])]
        piv = keep.pivot(index="scenario", columns="system", values=["recall", "attack_recall"]).round(2)
        lines += [f"## Per-scenario recall, {tier} tier", "", piv.to_markdown(), ""]
        lp = out / f"loso_{tier}.csv"
        if lp.exists():
            l = pd.read_csv(lp)
            h = l[(l.system == "hybrid") & (l.model == "random_forest")].pivot(index="scenario", columns="mode", values="recall")
            h["rules"] = l[l.system == "rules"].set_index("scenario").recall
            lines += [f"## Unseen-scenario recall (hybrid, RF), {tier} tier", "", h.round(2).to_markdown(), ""]
    (out / "results.md").write_text("\n".join(lines))
    print("wrote", out / "results.md")


if __name__ == "__main__":
    main()
