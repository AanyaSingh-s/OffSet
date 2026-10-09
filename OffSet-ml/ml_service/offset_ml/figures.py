"""Publication figures (IEEE column widths). Each figure plots a measured experimental result."""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from sklearn.decomposition import PCA
from sklearn.inspection import permutation_importance
from sklearn.metrics import precision_recall_curve, roc_curve
from sklearn.preprocessing import StandardScaler

from .config import figures_dir
from .evaluate import SCENARIOS, system_predictions
from .features import DEVICE_FEATURES, NATIVE_FEATURES
from .metrics import binary_metrics, hybrid_score, rank_metrics
from .training import TierResult, split_arrays

COL1, COL2 = 3.5, 7.16
C = {"rules": "#7f7f7f", "logistic_regression": "#1f77b4", "random_forest": "#d62728",
     "isolation_forest": "#2ca02c", "hybrid": "#000000"}
LABEL = {"rules_only": "Rules", "logistic_regression": "LR", "random_forest": "RF", "isolation_forest": "IF"}
SC_LABEL = {s: s.replace("_", " ") for s in SCENARIOS}


def style() -> None:
    plt.rcParams.update({
        "font.family": "serif", "font.serif": ["Times New Roman", "Liberation Serif", "DejaVu Serif"],
        "font.size": 8, "axes.labelsize": 8, "axes.titlesize": 8, "legend.fontsize": 7,
        "xtick.labelsize": 7, "ytick.labelsize": 7, "axes.linewidth": 0.6, "lines.linewidth": 1.2,
        "figure.dpi": 150, "savefig.dpi": 300, "savefig.bbox": "tight", "axes.grid": True, "grid.alpha": 0.25,
        "pdf.fonttype": 42,
    })


def save(fig, name: str) -> None:
    for ext in ("pdf", "png"):
        fig.savefig(figures_dir() / f"{name}.{ext}")
    plt.close(fig)


def _test(res: TierResult, df: pd.DataFrame):
    _, y, r, part = split_arrays(df, res.tier)["test"]
    return y, r, part


def confusion(res: TierResult, df: pd.DataFrame) -> None:
    y, r, _ = _test(res, df)
    preds = system_predictions(res, r)
    sel = res.selected
    panels = [("A: Rules only", preds["rules_only"]), (f"B: ML only ({LABEL[sel]})", preds[f"ml_{sel}"]),
              (f"C: Hybrid ({LABEL[sel]})", preds[f"hybrid_{sel}"])]
    fig, axes = plt.subplots(1, 3, figsize=(COL2, 2.3))
    for ax, (title, pred) in zip(axes, panels):
        m = binary_metrics(y, pred)
        mat = np.array([[m["tn"], m["fp"]], [m["fn"], m["tp"]]])
        norm = mat / mat.sum(axis=1, keepdims=True)
        ax.imshow(norm, cmap="Blues", vmin=0, vmax=1)
        for i in range(2):
            for j in range(2):
                ax.text(j, i, f"{mat[i, j]:,}\n({norm[i, j]:.1%})", ha="center", va="center",
                        color="white" if norm[i, j] > 0.5 else "black", fontsize=7)
        ax.set_xticks([0, 1], ["Pass", "Alert"])
        ax.set_yticks([0, 1], ["Legit", "Fraud"])
        ax.set_title(title)
        ax.grid(False)
    save(fig, "fig1_confusion_matrices")


def roc_pr(res: TierResult, df: pd.DataFrame) -> None:
    y, r, _ = _test(res, df)
    preds = system_predictions(res, r)
    for kind in ("roc", "pr"):
        fig, ax = plt.subplots(figsize=(COL1, 2.9))
        curves = [(LABEL[n], res.scores[n]["test"], C[n], "-") for n in res.models]
        sel = res.selected
        curves.append((f"Hybrid ({LABEL[sel]})", hybrid_score(res.scores[sel]["test"], r, res.thresholds[sel]["hybrid"]), C["hybrid"], "--"))
        for name, s, color, ls in curves:
            if kind == "roc":
                fpr, tpr, _ = roc_curve(y, s)
                ax.plot(fpr, tpr, color=color, ls=ls, label=f"{name} (AUC {rank_metrics(y, s)['roc_auc']:.3f})")
            else:
                p, rc, _ = precision_recall_curve(y, s)
                ax.plot(rc, p, color=color, ls=ls, label=f"{name} (AP {rank_metrics(y, s)['pr_auc']:.3f})")
        for name, pred, mk in (("Rules", preds["rules_only"], "s"), (f"Hybrid op. pt.", preds[f"hybrid_{sel}"], "o")):
            m = binary_metrics(y, pred)
            ax.scatter(*( (m["fpr"], m["recall"]) if kind == "roc" else (m["recall"], m["precision"])),
                       marker=mk, color=C["rules"] if name == "Rules" else "k", s=22, zorder=5, label=name)
        if kind == "roc":
            ax.plot([0, 1], [0, 1], color="#bbbbbb", lw=0.8)
            ax.set(xlabel="False positive rate", ylabel="True positive rate", xlim=(0, 1), ylim=(0, 1.01))
            ax.legend(loc="lower right")
            save(fig, "fig2_roc")
        else:
            ax.axhline(y.mean(), color="#bbbbbb", lw=0.8, label=f"Base rate {y.mean():.3f}")
            ax.set(xlabel="Recall", ylabel="Precision", xlim=(0, 1), ylim=(0, 1.02))
            ax.legend(loc="upper right")
            save(fig, "fig3_precision_recall")


def importance(res: TierResult, df: pd.DataFrame, seed: int = 0) -> pd.DataFrame:
    Xte, yte, _, _ = split_arrays(df, res.tier)["test"]
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(yte), size=min(6000, len(yte)), replace=False)
    model = res.models["random_forest"]
    pi = permutation_importance(model, Xte[idx], yte[idx], scoring="average_precision", n_repeats=3,
                                random_state=seed, n_jobs=1)
    imp = pd.DataFrame({"feature": res.features, "mean": pi.importances_mean, "std": pi.importances_std})
    imp = imp.sort_values("mean", ascending=False)
    top = imp.head(15).iloc[::-1]
    fig, ax = plt.subplots(figsize=(COL1, 3.3))
    colors = ["#d62728" if f in DEVICE_FEATURES else "#1f77b4" for f in top.feature]
    ax.barh(top.feature, top["mean"], xerr=top["std"], color=colors, error_kw={"lw": 0.6})
    ax.set(xlabel="Permutation importance (drop in average precision)")
    ax.grid(axis="y", visible=False)
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color="#1f77b4"), plt.Rectangle((0, 0), 1, 1, color="#d62728")],
              labels=["Repo-native feature", "Device-state feature"], loc="lower right")
    save(fig, "fig4_feature_importance")
    return imp


def isolation(res: TierResult, df: pd.DataFrame, seed: int = 0) -> None:
    Xte, yte, _, _ = split_arrays(df, res.tier)["test"]
    s = res.scores["isolation_forest"]["test"]
    th = res.thresholds["isolation_forest"]["hybrid"]
    fig, (a, b) = plt.subplots(1, 2, figsize=(COL2, 2.7))
    bins = np.linspace(s.min(), s.max(), 45)
    a.hist(s[yte == 0], bins=bins, alpha=0.65, color="#1f77b4", label="Legitimate", density=True)
    a.hist(s[yte == 1], bins=bins, alpha=0.65, color="#d62728", label="Fraud", density=True)
    a.axvline(th, color="k", ls="--", lw=0.9, label=f"Threshold {th:.3f}")
    a.set(xlabel="Isolation Forest score $s(x)=2^{-E[h(x)]/c(\\psi)}$", ylabel="Density")
    a.legend()
    a.set_title("(a) Score distribution")
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(yte), size=min(5000, len(yte)), replace=False)
    Z = PCA(n_components=2, random_state=seed).fit_transform(StandardScaler().fit_transform(Xte[idx]))
    order = np.argsort(yte[idx])
    sc = b.scatter(Z[order, 0], Z[order, 1], c=s[idx][order], cmap="viridis", s=4, alpha=0.6, linewidths=0)
    f = yte[idx] == 1
    b.scatter(Z[f, 0], Z[f, 1], facecolors="none", edgecolors="#d62728", s=14, linewidths=0.5, label="Fraud")
    fig.colorbar(sc, ax=b, label="Anomaly score")
    b.set(xlabel="PC 1", ylabel="PC 2")
    b.legend(loc="upper right")
    b.set_title("(b) Test sample, PCA projection")
    save(fig, "fig5_isolation_forest")


def pipeline_diagram(n_native: int, n_device: int) -> None:
    fig, ax = plt.subplots(figsize=(COL2, 3.0))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 6)
    ax.axis("off")

    def box(x, y, w, h, text, color):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05", fc=color, ec="k", lw=0.6))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=6.5)

    def arrow(x0, y0, x1, y1):
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops={"arrowstyle": "->", "lw": 0.8})

    box(0.1, 2.3, 2.2, 1.4, "Decrypted payment\n(sender, receiver, amount,\nnonce, signedAt)\n+ device fields*", "#e8e8e8")
    box(3.0, 2.3, 2.4, 1.4, "Per-user state\n(prior settled events,\nWelford stats, chain,\nseen nonces/hashes)", "#cfe2f3")
    box(6.1, 4.0, 2.7, 1.5, f"Native features ({n_native})\namount stats, z-score,\nwindows 10m/1h/24h,\nreceiver, time, queue, lag", "#d9ead3")
    box(6.1, 0.5, 2.7, 1.5, f"Device-state features ({n_device})\nbalance chain, sequence,\nsnapshot, offline time,\ndevice change*", "#fce5cd")
    box(9.5, 4.0, 2.0, 1.5, "Behavioural ML\nLR / RF / IF\nrisk score", "#d9d2e9")
    box(9.5, 0.5, 2.0, 1.5, "Deterministic rules\nnative + policy*\n(hard reject)", "#f4cccc")
    box(12.0, 2.3, 1.9, 1.4, "Decision\nACCEPT / FLAG /\nREJECT", "#fff2cc")
    arrow(2.3, 3.0, 3.0, 3.0)
    arrow(5.4, 3.3, 6.1, 4.6)
    arrow(5.4, 2.7, 6.1, 1.5)
    arrow(8.8, 4.75, 9.5, 4.75)
    arrow(5.4, 2.4, 9.5, 1.3)
    arrow(11.5, 4.5, 12.4, 3.7)
    arrow(11.5, 1.3, 12.4, 2.3)
    ax.text(7.0, 0.05, "* proposed extension fields, not present in the current repository", fontsize=6.5, style="italic")
    ax.text(5.6, 3.05, "t", fontsize=1, alpha=0)
    ax.set_title("Causal feature-engineering and decision pipeline (state updated only after scoring)", fontsize=8)
    save(fig, "fig6_feature_pipeline")


def scenario_performance(res: TierResult, scen: pd.DataFrame) -> None:
    sel = res.selected
    systems = [("rules_only", "Rules", C["rules"]), (f"ml_{sel}", f"ML ({LABEL[sel]})", C[sel]),
               (f"hybrid_{sel}", f"Hybrid ({LABEL[sel]})", "k")]
    panels = (("recall", "(a) Recall (transactions)"), ("attack_recall", "(b) Attack-level recall"),
              ("f1", "(c) One-vs-legitimate F1"))
    fig, axes = plt.subplots(1, 3, figsize=(COL2, 3.2), sharey=True)
    x = np.arange(len(SCENARIOS))
    for ax, (metric, title) in zip(axes, panels):
        for k, (key, name, color) in enumerate(systems):
            vals = [scen[(scen.system == key) & (scen.scenario == s)][metric].iloc[0] for s in SCENARIOS]
            ax.barh(x + (k - 1) * 0.27, vals, height=0.26, color=color, label=name)
        ax.set_yticks(x, [SC_LABEL[s] for s in SCENARIOS])
        ax.set(xlim=(0, 1.02), title=title)
        ax.invert_yaxis()
        ax.grid(axis="y", visible=False)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.04))
    save(fig, "fig7_scenario_performance")


def model_comparison(overall: dict[str, pd.DataFrame], selected: dict[str, str]) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(COL2, 2.8), sharey=True)
    metrics = ["precision", "recall", "f1", "pr_auc", "fpr"]
    for ax, (tier, tab) in zip(axes, overall.items()):
        sel = selected[tier]
        systems = [("rules_only", "Rules", C["rules"]), ("ml_logistic_regression", "LR", C["logistic_regression"]),
                   ("ml_random_forest", "RF", C["random_forest"]), ("ml_isolation_forest", "IF", C["isolation_forest"]),
                   (f"hybrid_{sel}", f"Hybrid ({LABEL[sel]})", "k")]
        w = 0.16
        for k, (key, name, color) in enumerate(systems):
            row = tab[tab.system == key].iloc[0]
            vals = [0 if np.isnan(row[m]) else row[m] for m in metrics]
            ax.bar(np.arange(len(metrics)) + (k - 2) * w, vals, w, color=color, label=name)
        ax.set_xticks(range(len(metrics)), ["Precision", "Recall", "F1", "PR-AUC", "FPR"])
        ax.set_title(f"({'a' if tier == 'native' else 'b'}) {'Repo-native' if tier == 'native' else 'Extended'} features/rules")
        ax.set_ylim(0, 1.02)
        ax.grid(axis="x", visible=False)
    axes[0].legend(ncol=2, loc="upper left")
    axes[0].set_ylabel("Test-set value")
    save(fig, "fig8_model_comparison")


def behaviour(df: pd.DataFrame) -> None:
    test = df[(df.split == "test") & (df.outcome != "DUPLICATE")]
    feats = [("amount_zscore", "Amount z-score"), ("cnt_1h", "Prior tx in last hour"),
             ("log_queue_spend", "ln(1 + queue spend)"), ("log_offline_min", "ln(1 + offline minutes)"),
             ("chain_gap", "Balance-chain gap (signed ln)"), ("hour_share", "Hour-of-day share")]
    fig, axes = plt.subplots(2, 3, figsize=(COL2, 3.8))
    for ax, (col, title) in zip(axes.ravel(), feats):
        data = [test[test.fraud_label == 0][col], test[test.fraud_label == 1][col]]
        bp = ax.boxplot(data, widths=0.55, patch_artist=True, showfliers=False, tick_labels=["Legit", "Fraud"])
        for patch, color in zip(bp["boxes"], ("#9ecae1", "#fc9272")):
            patch.set_facecolor(color)
        ax.set_title(title)
        ax.grid(axis="x", visible=False)
    save(fig, "fig9_behaviour_legit_vs_fraud")


def unseen(loso: pd.DataFrame, tier: str) -> None:
    sub = loso[(loso.system == "hybrid") & (loso["mode"].isin(["seen", "unseen"]))]
    models = [("random_forest", "RF"), ("logistic_regression", "LR"), ("isolation_forest", "IF")]
    rules_rec = loso[loso.system == "rules"].set_index("scenario").recall
    fig, axes = plt.subplots(1, 3, figsize=(COL2, 3.0), sharey=True)
    y = np.arange(len(SCENARIOS))
    for ax, (m, lab) in zip(axes, models):
        for k, (mode, color) in enumerate((("seen", "#9ecae1"), ("unseen", "#d62728"))):
            part = sub[(sub.model == m) & (sub["mode"] == mode)].set_index("scenario").recall
            ax.barh(y + (k - 0.5) * 0.36, [part[s] for s in SCENARIOS], 0.35, color=color,
                    label="Scenario in training" if mode == "seen" else "Scenario held out")
        ax.scatter([rules_rec[s] for s in SCENARIOS], y, marker="|", color="k", s=40, label="Rules only", zorder=5)
        ax.set_title(f"Hybrid with {lab}")
        ax.set_xlim(0, 1.02)
        ax.grid(axis="y", visible=False)
        ax.set_xlabel("Recall")
    axes[0].set_yticks(y, [SC_LABEL[s] for s in SCENARIOS])
    axes[0].invert_yaxis()
    axes[0].legend(loc="lower right", fontsize=6)
    save(fig, f"fig10_unseen_scenarios_{tier}")


def threshold_analysis(res: TierResult, df: pd.DataFrame, beta: float) -> None:
    _, yva, rva, _ = split_arrays(df, res.tier)["val"]
    sel = res.selected
    s = res.scores[sel]["val"]
    th = res.thresholds[sel]
    grid = np.unique(np.quantile(s[~rva], np.linspace(0.5, 0.9995, 200)))
    rows = []
    for t in grid:
        m = binary_metrics(yva, rva | (s >= t))
        b2 = beta ** 2
        fb = (1 + b2) * m["tp"] / max((1 + b2) * m["tp"] + b2 * m["fn"] + m["fp"], 1e-12)
        rows.append((t, m["precision"], m["recall"], m["fpr"], fb))
    arr = np.array(rows)
    fig, ax = plt.subplots(figsize=(COL1, 2.8))
    for col, name, ls in ((1, "Precision", "-"), (2, "Recall", "-"), (3, "FPR", ":"), (4, f"F{beta:.0f}", "--")):
        ax.plot(arr[:, 0], arr[:, col], ls=ls, label=name)
    ax.axvline(th["hybrid"], color="k", lw=0.8, label=f"Chosen t={th['hybrid']:.3f}")
    if th["high"] <= 1:
        ax.axvline(th["high"], color="#d62728", lw=0.8, ls="-.", label=f"HIGH t={th['high']:.3f}")
    ax.set(xlabel=f"ML threshold ({LABEL[sel]}), validation users", ylabel="Hybrid system metric", ylim=(0, 1.02))
    ax.legend(fontsize=6)
    save(fig, "fig11_threshold_analysis")
