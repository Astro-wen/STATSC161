"""Reproduce the wallet purchase price study without loading the confirmed flag.

Run with Python 3.12 and the packages in requirements.txt. Data, figures,
tables, and models are located relative to the wallet_analysis project root.
"""
from pathlib import Path
import os
import sys

OUT = Path(__file__).resolve().parents[1]
LOCAL_DEPS = OUT / ".build" / "python_deps"
# Reuse the existing local package cache without moving project folders.
if not LOCAL_DEPS.exists():
    LOCAL_DEPS = OUT / "outputs" / "purchase_price_research" / ".build" / "python_deps"
if LOCAL_DEPS.exists():
    sys.path.insert(0, str(LOCAL_DEPS))
os.environ.setdefault("MPLCONFIGDIR", str(OUT / ".build" / "matplotlib"))
os.environ.setdefault("OMP_NUM_THREADS", "4")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "4")

import csv
import hashlib
import json
import platform
import time
import warnings
import numpy as np
import pandas as pd
import scipy
import sklearn
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, KFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler
from threadpoolctl import threadpool_limits
import joblib

SOURCE = OUT / "data" / "wallet_features.csv"
TARGET = "avg_buy_price"
FEATURES = ["trade_count", "unique_markets", "wallet_age_days", "concentration", "total_notional", "max_single_buy"]
ACTIVITY = FEATURES[:4]
LOG_COLS = [f for f in FEATURES if f != "concentration"]
LABELS = {
    "trade_count": "Trade count", "unique_markets": "Markets traded",
    "wallet_age_days": "Observed activity span", "concentration": "Spending concentration",
    "total_notional": "Total spending", "max_single_buy": "Largest single purchase",
    TARGET: "Average purchase price",
}
PRIMARY = ["Mean baseline", "Linear regression", "Gradient boosting"]
COLORS = {"Mean baseline": "#9AA4B2", "Median baseline": "#CBD0D8", "Linear regression": "#315C8C", "Gradient boosting": "#DF7137", "Activity only linear": "#87A6C9", "Activity only boosting": "#E6AE86"}
GRID = {"model__max_leaf_nodes": [7, 15, 31], "model__l2_regularization": [0.0, 1.0]}
FIGURES = []
START = time.perf_counter()

for directory in ["figures", "tables", "models", ".build"]:
    (OUT / directory).mkdir(exist_ok=True, parents=True)

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10.5, "axes.titlesize": 12, "axes.labelsize": 10.5, "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": "#CBD0D8", "axes.labelcolor": "#263449", "text.color": "#263449", "xtick.color": "#556276", "ytick.color": "#556276", "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white", "grid.color": "#E8ECF1", "grid.linewidth": .7, "figure.dpi": 120, "savefig.dpi": 220})


def savefig(fig, stem, title, caption, audience="report"):
    fig.savefig(OUT / "figures" / f"{stem}.png", bbox_inches="tight")
    fig.savefig(OUT / "figures" / f"{stem}.svg", bbox_inches="tight")
    plt.close(fig)
    FIGURES.append({"id": stem, "title": title, "caption": caption, "audience": audience})


def table(df, stem, index=False):
    df.to_csv(OUT / "tables" / f"{stem}.csv", index=index, float_format="%.10g")


def preprocessor(features):
    logs = [f for f in features if f != "concentration"]
    return ColumnTransformer([("log", FunctionTransformer(np.log1p, feature_names_out="one-to-one"), logs), ("concentration", "passthrough", ["concentration"])], verbose_feature_names_out=False)


def linear(features):
    return Pipeline([("prepare", preprocessor(features)), ("scale", StandardScaler()), ("model", LinearRegression())])


def boosting(features):
    return Pipeline([("prepare", preprocessor(features)), ("model", HistGradientBoostingRegressor(loss="squared_error", learning_rate=.06, max_iter=250, min_samples_leaf=30, max_bins=255, early_stopping=False, categorical_features=None, random_state=42))])


def metrics(y, prediction):
    return {"MAE": float(mean_absolute_error(y, prediction)), "RMSE": float(np.sqrt(mean_squared_error(y, prediction))), "R2": float(r2_score(y, prediction))}


def summarize_bins(x, y, q=10):
    frame = pd.DataFrame({"x": np.asarray(x), "y": np.asarray(y)})
    frame["bin"] = pd.qcut(frame.x, q=q, duplicates="drop")
    return frame.groupby("bin", observed=True).agg(x=("x", "median"), mean_x=("x", "mean"), mean=("y", "mean"), median=("y", "median"), lower=("y", lambda z: z.quantile(.25)), upper=("y", lambda z: z.quantile(.75)), n=("y", "size"), sd=("y", "std")).reset_index(drop=True)


def run():
    # The ignored label is deliberately absent from usecols.
    with SOURCE.open() as handle:
        header = next(csv.reader(handle))
    data = pd.read_csv(SOURCE, usecols=["wallet", TARGET] + FEATURES)
    assert "confirmed" not in data.columns
    assert not data.wallet.duplicated().any(), "Wallet IDs must be unique."
    assert not data[[TARGET] + FEATURES].isna().any().any()
    assert np.isfinite(data[[TARGET] + FEATURES].to_numpy()).all()
    assert data[TARGET].between(0, 1).all()
    assert (data[LOG_COLS] >= 0).all().all()
    assert data.concentration.between(0, 1).all()
    assert (data.unique_markets <= data.trade_count).all()
    assert (data.max_single_buy <= data.total_notional + 1e-6).all()
    assert (data.concentration + 1e-6 >= 1 / data.unique_markets).all()
    train_ids, test_ids = train_test_split(np.arange(len(data)), test_size=.20, random_state=42, shuffle=True)
    assert not set(train_ids) & set(test_ids)
    train, test = data.iloc[train_ids].copy(), data.iloc[test_ids].copy()
    Xtrain, Xtest = train[FEATURES], test[FEATURES]
    ytrain, ytest = train[TARGET], test[TARGET]
    folds = list(KFold(n_splits=5, shuffle=True, random_state=42).split(Xtrain))
    assert all(not set(a) & set(b) for a, b in folds)
    split = pd.DataFrame({"wallet": data.wallet, "split": np.where(np.isin(np.arange(len(data)), train_ids), "train", "test")})
    table(split, "wallet_split")
    audit = {"rows": len(data), "original_column_count": len(header), "loaded_column_count": len(data.columns), "unique_wallets": int(data.wallet.nunique()), "missing_selected_values": int(data.isna().sum().sum()), "nonfinite_selected_numeric_values": int((~np.isfinite(data[[TARGET] + FEATURES])).sum().sum()), "duplicate_wallets": int(data.wallet.duplicated().sum()), "excluded_rows": 0, "train_rows": len(train), "test_rows": len(test), "train_test_overlap": 0, "flag_loaded": False, "single_market_wallets": int(data.unique_markets.eq(1).sum()), "zero_span_wallets": int(data.wallet_age_days.eq(0).sum()), "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(), "source": str(SOURCE), "features": FEATURES, "target": TARGET, "random_seed": 42, "train_target_mean": float(ytrain.mean()), "train_target_median": float(ytrain.median()), "target_min": float(data[TARGET].min()), "target_max": float(data[TARGET].max())}
    descriptive = data[[TARGET] + FEATURES].describe(percentiles=[.01, .10, .25, .50, .75, .90, .99]).T
    descriptive["zeros"] = data[[TARGET] + FEATURES].eq(0).sum()
    descriptive["skewness"] = data[[TARGET] + FEATURES].skew()
    table(descriptive.reset_index(names="variable"), "descriptive_statistics")
    split_summary = pd.DataFrame([{"split": name, "n": len(frame), "target_mean": frame[TARGET].mean(), "target_median": frame[TARGET].median(), "target_sd": frame[TARGET].std(), "target_q10": frame[TARGET].quantile(.1), "target_q90": frame[TARGET].quantile(.9)} for name, frame in [("train", train), ("test", test)]])
    table(split_summary, "split_summary")
    print("Data checks passed:", json.dumps(audit), flush=True)

    # Development figures use training data only.
    counts, edges = np.histogram(ytrain, bins=np.linspace(0, 1, 26))
    table(pd.DataFrame({"bin_left": edges[:-1], "bin_right": edges[1:], "wallets": counts, "fraction": counts/len(train)}), "target_histogram_training")
    fig, ax = plt.subplots(figsize=(8.6, 4.7), layout="constrained")
    ax.hist(ytrain, bins=edges, weights=np.ones(len(train))/len(train), color="#315C8C", edgecolor="white", linewidth=.7)
    ax.axvline(ytrain.mean(), color="#DF7137", lw=2, label=f"Training mean {ytrain.mean():.3f}")
    ax.axvline(ytrain.median(), color="#263449", lw=1.5, ls="--", label=f"Training median {ytrain.median():.3f}")
    ax.set(xlim=(0,1), xlabel="Average purchase price ($ per share)", ylabel="Share of training wallets", title="Average purchase prices vary widely across wallets")
    ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.legend(frameon=False, loc="upper left")
    savefig(fig, "01_target_distribution", "Distribution of average purchase price", "Training wallets only. Each wallet receives equal weight. Prices summarize shares bought across different markets.", "report and slide 1")

    fig, axes = plt.subplots(2, 3, figsize=(11.2, 6.5), layout="constrained")
    for ax, feature in zip(axes.flat, FEATURES):
        values = train[feature] if feature == "concentration" else np.log1p(train[feature])
        ax.hist(values, bins=35, color="#315C8C", alpha=.9, edgecolor="white", linewidth=.3)
        ax.set(title=LABELS[feature], xlabel="Original proportion" if feature == "concentration" else "log(1 + original value)", ylabel="Training wallets")
    savefig(fig, "02_predictor_distributions", "Predictor distributions after transformation", "Five nonnegative predictors use log(1+x). Concentration remains on its original scale. No trimming or winsorization.")

    corr = train[FEATURES + [TARGET]].corr(method="spearman")
    table(corr.reset_index(names="variable"), "spearman_correlations_training")
    fig, ax = plt.subplots(figsize=(8.2, 7.0), layout="constrained")
    im = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(7), [LABELS[f] for f in corr.columns], rotation=43, ha="right")
    ax.set_yticks(range(7), [LABELS[f] for f in corr.index])
    for i in range(7):
        for j in range(7):
            ax.text(j, i, f"{corr.iloc[i,j]:.2f}", ha="center", va="center", color="white" if abs(corr.iloc[i,j])>.63 else "#263449", fontsize=9)
    fig.colorbar(im, ax=ax, fraction=.04, pad=.02, label="Spearman rank correlation")
    ax.set_title("Correlated predictors complicate individual attribution")
    savefig(fig, "03_rank_correlations", "Rank correlations", "Training data only. Rank correlations summarize monotonic relationships and do not establish causation.")

    fig, axes = plt.subplots(2, 3, figsize=(11.2, 6.6), layout="constrained", sharey=True)
    binned_rows = []
    for ax, feature in zip(axes.flat, FEATURES):
        b = summarize_bins(train[feature], ytrain)
        b["variable"] = feature
        binned_rows.append(b)
        x = b.x if feature == "concentration" else np.log1p(b.x)
        ax.fill_between(x, b.lower, b.upper, color="#315C8C", alpha=.13, label="Middle 50% of prices")
        ax.plot(x, b["mean"], "o-", color="#315C8C", ms=4, label="Mean price")
        ax.set(title=LABELS[feature], ylim=(0,1), xlabel="Original proportion" if feature == "concentration" else "log(1 + bin median)", ylabel="Average purchase price ($)")
    axes.flat[0].legend(frameon=False, fontsize=8)
    table(pd.concat(binned_rows, ignore_index=True), "binned_associations_training")
    savefig(fig, "04_binned_associations", "Observed price patterns by predictor", "Training wallets in approximately equal-frequency bins. Shading shows the interquartile range of observed prices, not a confidence interval. Discrete predictors can produce fewer than ten bins.")

    # All model choices and supplementary specifications precede test evaluation.
    models = {"Mean baseline": DummyRegressor(strategy="mean"), "Median baseline": DummyRegressor(strategy="median"), "Linear regression": linear(FEATURES), "Activity only linear": linear(ACTIVITY)}
    cv_scores = {}
    for name, model in models.items():
        cols = ACTIVITY if "Activity" in name else FEATURES
        cv_scores[name] = -cross_val_score(model, train[cols], ytrain, cv=folds, scoring="neg_mean_absolute_error", n_jobs=1)
        model.fit(train[cols], ytrain)
        print("Fitted", name, "CV MAE", cv_scores[name].mean(), flush=True)
    searches = {}
    for name, features in [("Gradient boosting", FEATURES), ("Activity only boosting", ACTIVITY)]:
        search = GridSearchCV(boosting(features), GRID, scoring="neg_mean_absolute_error", cv=folds, refit=True, n_jobs=1, return_train_score=True, error_score="raise")
        search.fit(train[features], ytrain)
        searches[name] = search
        models[name] = search.best_estimator_
        cv_scores[name] = -np.array([search.cv_results_[f"split{i}_test_score"][search.best_index_] for i in range(5)])
        grid_table = pd.DataFrame(search.cv_results_)
        grid_table["mean_validation_mae"] = -grid_table.mean_test_score
        grid_table["mean_training_mae"] = -grid_table.mean_train_score
        table(grid_table, "cv_grid_full" if features == FEATURES else "cv_grid_activity_only")
        print("Selected", name, search.best_params_, "CV MAE", -search.best_score_, flush=True)

    selection = {name: {"best_parameters": search.best_params_, "best_cv_mae": float(-search.best_score_), "candidates": len(search.cv_results_["params"])} for name, search in searches.items()}
    cv_rows = [{"model": name, "fold": i+1, "MAE": float(value)} for name, scores in cv_scores.items() for i, value in enumerate(scores)]
    table(pd.DataFrame(cv_rows), "cv_fold_scores")
    (OUT / "tables" / "model_selection.json").write_text(json.dumps(selection, indent=2))

    fig, ax = plt.subplots(figsize=(8.8, 4.5), layout="constrained")
    cv_grid = pd.DataFrame(searches["Gradient boosting"].cv_results_)
    positions = np.arange(len(cv_grid))
    grid_values = [-np.array([row[f"split{i}_test_score"] for i in range(5)])*100 for _,row in cv_grid.iterrows()]
    ax.boxplot(grid_values, tick_labels=[f"{int(row.param_model__max_leaf_nodes)} leaves\nL2 {float(row.param_model__l2_regularization):g}" for _,row in cv_grid.iterrows()], patch_artist=True, boxprops={"facecolor":"#DCE6F1", "edgecolor":"#315C8C"}, medianprops={"color":"#DF7137"}, widths=.5)
    ax.set(xlabel="Gradient boosting candidates", ylabel="Validation MAE (cents per share)", title="Model complexity selected using training folds")
    ax.grid(axis="y", alpha=.8)
    savefig(fig, "05_cross_validation", "Cross validation for gradient boosting", "Five validation-fold errors per candidate. The search varies maximum leaves and L2 regularization while keeping other settings fixed. Fold variability is not a confidence interval.")

    print("Model selection locked. Evaluating the untouched test wallets.", flush=True)
    predictions = {}
    performance = []
    for name, model in models.items():
        cols = ACTIVITY if "Activity" in name else FEATURES
        prediction = model.predict(test[cols])
        assert np.isfinite(prediction).all()
        predictions[name] = prediction
        train_metrics = metrics(ytrain, model.predict(train[cols]))
        row = {"model": name, **metrics(ytest, prediction), "CV_MAE": float(cv_scores[name].mean()), "CV_MAE_SD": float(cv_scores[name].std(ddof=1)), "train_MAE": train_metrics["MAE"], "train_R2": train_metrics["R2"], "outside_0_1": int(((prediction<0)|(prediction>1)).sum())}
        performance.append(row)
        joblib.dump(model, OUT / "models" / (name.lower().replace(" ", "_") + ".joblib"))
    result = pd.DataFrame(performance).set_index("model")
    yarray = ytest.to_numpy()
    abs_errors = {name: np.abs(yarray - pred) for name, pred in predictions.items()}
    rng = np.random.default_rng(2026)
    bootstrap_mae = {name: np.empty(2000) for name in models}
    for b in range(2000):
        ix = rng.integers(0, len(test), len(test))
        for name in models:
            bootstrap_mae[name][b] = abs_errors[name][ix].mean()
    for name in models:
        lo, hi = np.quantile(bootstrap_mae[name], [.025, .975])
        result.loc[name, "MAE_CI_low"] = lo
        result.loc[name, "MAE_CI_high"] = hi
        result.loc[name, "MAE_cents"] = result.loc[name,"MAE"]*100
    comparisons = []
    for reference in ["Mean baseline", "Median baseline", "Linear regression", "Activity only boosting"]:
        delta = bootstrap_mae[reference] - bootstrap_mae["Gradient boosting"]
        comparisons.append({"comparison": f"{reference} minus Gradient boosting", "mae_reduction": float(result.loc[reference,"MAE"]-result.loc["Gradient boosting","MAE"]), "ci_low": float(np.quantile(delta,.025)), "ci_high": float(np.quantile(delta,.975)), "percent_reduction": float(100*(1-result.loc["Gradient boosting","MAE"]/result.loc[reference,"MAE"]))})
    table(result.reset_index(), "all_model_metrics")
    table(result.loc[PRIMARY].reset_index(), "primary_model_metrics")
    table(pd.DataFrame(comparisons), "paired_bootstrap_comparisons")
    prediction_table = test[["wallet",TARGET] + FEATURES].copy()
    for name, prediction in predictions.items():
        prediction_table[name.lower().replace(" ", "_")] = prediction
    table(prediction_table, "test_predictions")

    fig, ax = plt.subplots(figsize=(8.8,4.6), layout="constrained")
    for i, name in enumerate(PRIMARY):
        row = result.loc[name]
        ax.barh(i, row.MAE*100, height=.54, color=COLORS[name])
        ax.errorbar(row.MAE*100, i, xerr=[[100*(row.MAE-row.MAE_CI_low)], [100*(row.MAE_CI_high-row.MAE)]], fmt="none", ecolor="#263449", capsize=4)
        ax.text(row.MAE*100+.65, i, f"{row.MAE*100:.2f} cents", va="center", fontsize=12, fontweight="bold")
    ax.set_yticks(range(3), PRIMARY)
    ax.invert_yaxis()
    ax.set(xlim=(0,result.loc[PRIMARY,"MAE"].max()*100+5), xlabel="Test MAE (cents per share, lower is better)", title="Prediction error on the same held out wallets")
    ax.grid(axis="x", alpha=.8)
    ax.set_axisbelow(True)
    savefig(fig, "06_test_model_comparison", "Test prediction error", "Primary models evaluated on identical test wallets. Error bars are 95% paired wallet-bootstrap intervals conditional on the fitted models. Each wallet has equal weight.", "report and slide 3")

    fig, axes = plt.subplots(1,2,figsize=(10.2,4.8),layout="constrained",sharex=True,sharey=True)
    density_plots=[]
    for ax,name in zip(axes,["Linear regression","Gradient boosting"]):
        hb=ax.hexbin(yarray,predictions[name],gridsize=40,mincnt=1,bins="log",cmap="Blues",extent=(0,1,-.1,1.1))
        density_plots.append(hb)
        ax.plot([0,1],[0,1],color="#DF7137",lw=1.5)
        ax.set(title=name,xlabel="Observed average price ($)",ylabel="Predicted average price ($)",xlim=(0,1),ylim=(-.1,1.1))
    common_norm=matplotlib.colors.LogNorm(vmin=1,vmax=max(float(h.get_array().max()) for h in density_plots))
    for h in density_plots: h.set_norm(common_norm)
    fig.colorbar(hb,ax=axes,label="Wallet count (log scale)",fraction=.025,pad=.02)
    savefig(fig,"07_observed_vs_predicted","Observed and predicted prices","Test wallets. The diagonal represents perfect prediction. Predictions remain unclipped for the primary evaluation.")

    fig,axes=plt.subplots(1,2,figsize=(10.2,4.6),layout="constrained",sharey=True)
    for ax,name in zip(axes,["Linear regression","Gradient boosting"]):
        residual=yarray-predictions[name]
        ax.hexbin(predictions[name],residual,gridsize=40,mincnt=1,bins="log",cmap="Blues",extent=(-.1,1.1,-1,1))
        ax.axhline(0,color="#DF7137",lw=1.5)
        ax.set(title=name,xlabel="Predicted average price ($)",ylabel="Observed minus predicted ($)",xlim=(-.1,1.1),ylim=(-1,1))
    savefig(fig,"08_residual_patterns","Residuals versus predicted price","Test wallets. Positive residuals mean underprediction. The bounded target naturally constrains the residual envelope.")

    fig,axes=plt.subplots(1,2,figsize=(10.2,4.6),layout="constrained")
    for name in PRIMARY:
        axes[0].hist(yarray-predictions[name],bins=np.linspace(-1,1,65),histtype="step",density=True,lw=1.6,color=COLORS[name],label=name)
        err=np.sort(abs_errors[name])
        axes[1].plot(err*100,np.arange(1,len(err)+1)/len(err),color=COLORS[name],lw=2,label=name)
    axes[0].set(xlabel="Observed minus predicted ($)",ylabel="Density",title="Residual distributions",xlim=(-.8,.8))
    axes[1].set(xlabel="Absolute error (cents per share)",ylabel="Share of test wallets",title="Cumulative absolute error",xlim=(0,80),ylim=(0,1))
    axes[1].yaxis.set_major_formatter(PercentFormatter(1))
    axes[1].legend(frameon=False,fontsize=9)
    savefig(fig,"09_error_distributions","Distributions of prediction errors","Test wallets. The cumulative curve gives the proportion of wallets predicted within a specified absolute error.")

    calibration=[]
    fig,ax=plt.subplots(figsize=(7.4,5),layout="constrained")
    for name in ["Linear regression","Gradient boosting"]:
        b=summarize_bins(predictions[name],yarray)
        b["x"]=b["mean_x"]
        b["model"]=name
        calibration.append(b)
        ax.errorbar(b.x,b["mean"],yerr=1.96*b.sd/np.sqrt(b.n),color=COLORS[name],fmt="o-",lw=1.7,ms=5,capsize=3,label=name)
    ax.plot([0,1],[0,1],color="#9AA4B2",ls="--")
    ax.set(xlim=(0,1),ylim=(0,1),xlabel="Mean predicted price within bin ($)",ylabel="Mean observed price within bin ($)",title="Average observed prices across prediction bins")
    ax.legend(frameon=False)
    table(pd.concat(calibration,ignore_index=True),"calibration_bins_test")
    savefig(fig,"10_calibration","Binned calibration","Ten approximately equal-frequency prediction bins per model. Bars are approximate 95% intervals for observed bin means under wallet independence. Good average calibration can coexist with large individual errors.")

    error_groups=[]
    cuts=np.quantile(ytrain,np.linspace(0,1,6))
    cuts[0],cuts[-1]=-np.inf,np.inf
    test_bins=pd.cut(ytest,bins=np.unique(cuts),labels=False,include_lowest=True)
    for i in sorted(test_bins.unique()):
        mask=(test_bins==i).to_numpy()
        for name in PRIMARY:
            error_groups.append({"price_group":int(i)+1,"model":name,"n":int(mask.sum()),"observed_mean":float(yarray[mask].mean()),**metrics(yarray[mask],predictions[name][mask])})
    errors_df=pd.DataFrame(error_groups)
    table(errors_df,"error_by_price_group")
    fig,ax=plt.subplots(figsize=(8.8,4.6),layout="constrained")
    for name in PRIMARY:
        rows=errors_df[errors_df.model==name]
        ax.plot(rows.price_group,rows.MAE*100,"o-",color=COLORS[name],label=name,lw=2)
    ax.set_xticks(range(1,6),["Lowest","2","3","4","Highest"])
    ax.set(xlabel="Observed price group (training quintile boundaries)",ylabel="Test MAE (cents per share)",title="Error depends on the price level")
    ax.legend(frameon=False)
    ax.grid(axis="y")
    savefig(fig,"11_error_by_price","Prediction error by observed price group","Test groups use price quintile boundaries fixed from the training set. Group membership uses the observed target and is descriptive only.")

    print("Computing interpretation diagnostics without refitting the selected models.",flush=True)
    perm=permutation_importance(models["Gradient boosting"],Xtest,ytest,scoring="neg_mean_absolute_error",n_repeats=20,random_state=2026,n_jobs=1)
    importance=pd.DataFrame({"variable":FEATURES,"increase_MAE":perm.importances_mean,"shuffle_sd":perm.importances_std,"increase_MAE_cents":perm.importances_mean*100,"shuffle_sd_cents":perm.importances_std*100}).sort_values("increase_MAE",ascending=False)
    table(importance,"permutation_importance_test")
    table(pd.DataFrame(perm.importances.T,columns=FEATURES).reset_index(names="shuffle"),"permutation_repeats")
    fig,ax=plt.subplots(figsize=(8.8,4.7),layout="constrained")
    rows=importance.iloc[::-1]
    ax.barh([LABELS[f] for f in rows.variable],rows.increase_MAE_cents,color="#315C8C",height=.62,xerr=rows.shuffle_sd_cents,error_kw={"ecolor":"#263449","capsize":3})
    ax.axvline(0,color="#9AA4B2",lw=1)
    ax.set(xlabel="Increase in test MAE after shuffling (cents per share)",title="Which predictors does gradient boosting rely on?")
    ax.grid(axis="x")
    ax.set_axisbelow(True)
    savefig(fig,"12_permutation_importance","Permutation feature importance","Gradient boosting on test wallets, 20 shuffles per predictor. Bars show mean increases in MAE and error bars show shuffle standard deviations. Correlated predictors can share or distort importance. Importance gives neither effect direction nor a causal effect.","report and slide 4")

    names=models["Linear regression"].named_steps["prepare"].get_feature_names_out().tolist()
    coef=models["Linear regression"].named_steps["model"].coef_
    coeff=pd.DataFrame({"variable":names,"coefficient_per_training_SD":coef,"coefficient_cents":coef*100}).sort_values("coefficient_per_training_SD")
    table(coeff,"linear_coefficients")
    fig,ax=plt.subplots(figsize=(8.8,4.6),layout="constrained")
    ax.barh([LABELS[f] for f in coeff.variable],coeff.coefficient_cents,color=["#315C8C" if v<0 else "#DF7137" for v in coeff.coefficient_cents],height=.6)
    ax.axvline(0,color="#263449",lw=1)
    ax.set(xlabel="Predicted price difference per 1 training SD (cents)",title="Conditional associations in the linear model")
    savefig(fig,"13_linear_coefficients","Standardized linear coefficients","Predictors use the stated log transforms followed by training-fitted standardization. Coefficients hold the other included predictors fixed. Correlation and model misspecification limit interpretation. No causal interpretation or coefficient significance tests.")

    ablation_names=["Activity only linear","Linear regression","Activity only boosting","Gradient boosting"]
    fig,ax=plt.subplots(figsize=(8.8,4.7),layout="constrained")
    for i,name in enumerate(ablation_names):
        row=result.loc[name]
        ax.barh(i,row.MAE*100,color=COLORS[name],height=.6)
        ax.text(row.MAE*100+.45,i,f"{row.MAE*100:.2f}",va="center",fontweight="bold")
    ax.set_yticks(range(4),["Linear: activity + concentration","Linear: all six predictors","Boosting: activity + concentration","Boosting: all six predictors"])
    ax.invert_yaxis()
    ax.set(xlim=(0,result.loc[ablation_names,"MAE"].max()*100+3),xlabel="Test MAE (cents per share)",title="What do spending and purchase size add?")
    ax.grid(axis="x")
    ax.set_axisbelow(True)
    savefig(fig,"14_spending_ablation","Sensitivity to monetary predictors","The four-predictor specification excludes total spending and largest purchase. Both boosting specifications use the same training-only tuning procedure. All inputs still summarize the same observed trading period.")

    subgroup_rows=[]
    masks={"One market":test.unique_markets.eq(1).to_numpy(),"Multiple markets":test.unique_markets.gt(1).to_numpy(),"Zero observed span":test.wallet_age_days.eq(0).to_numpy(),"Positive observed span":test.wallet_age_days.gt(0).to_numpy(),"High activity rule":((test.unique_markets>=500)|(test.trade_count>=2000)).to_numpy(),"Other activity":((test.unique_markets<500)&(test.trade_count<2000)).to_numpy()}
    for group,mask in masks.items():
        for name in PRIMARY:
            subgroup_rows.append({"group":group,"model":name,"n":int(mask.sum()),**metrics(yarray[mask],predictions[name][mask])})
    subgroup_df=pd.DataFrame(subgroup_rows)
    table(subgroup_df,"error_by_wallet_group")
    fig,ax=plt.subplots(figsize=(9.2,4.8),layout="constrained")
    groups=["One market","Multiple markets","Zero observed span","Positive observed span","High activity rule","Other activity"]
    y=np.arange(len(groups))
    for j,name in enumerate(["Linear regression","Gradient boosting"]):
        rows=subgroup_df.set_index(["model","group"]).loc[name].loc[groups]
        ax.barh(y+(j-.5)*.3,rows.MAE*100,height=.29,color=COLORS[name],label=name)
    sizes=subgroup_df[subgroup_df.model=="Mean baseline"].set_index("group").n
    ax.set_yticks(y,[f"{g} (n={sizes[g]:,})" for g in groups])
    ax.invert_yaxis()
    ax.set(xlabel="Test MAE (cents per share)",title="Performance varies across wallet groups")
    ax.legend(frameon=False,loc="lower right")
    savefig(fig,"15_wallet_subgroups","Prediction error by wallet subgroup","Test subgroups overlap. The high activity rule is at least 500 markets or 2,000 trades. Every group remains in model fitting. Small subgroups support limited precision.")

    bounds=[]
    for name in ["Linear regression","Gradient boosting"]:
        bounds.append({"model":name,**metrics(ytest,np.clip(predictions[name],0,1)),"clipped_predictions":int(((predictions[name]<0)|(predictions[name]>1)).sum())})
    table(pd.DataFrame(bounds),"clipping_sensitivity")
    transformed=models["Linear regression"].named_steps["scale"].transform(models["Linear regression"].named_steps["prepare"].transform(Xtrain))
    condition=float(np.linalg.cond(np.column_stack([np.ones(len(train)),transformed])))
    diagnostics={"scaled_design_condition_number":condition,"test_y_sd":float(ytest.std()),"boosting_error_within_5_cents":float((abs_errors["Gradient boosting"]<=.05).mean()),"boosting_error_within_10_cents":float((abs_errors["Gradient boosting"]<=.10).mean()),"boosting_error_within_20_cents":float((abs_errors["Gradient boosting"]<=.20).mean()),"OLS_outside_bounds":int(result.loc["Linear regression","outside_0_1"]),"boosting_outside_bounds":int(result.loc["Gradient boosting","outside_0_1"]),"bootstrap_repetitions":2000,"permutation_repetitions":20,"fit_runtime_seconds":float(time.perf_counter()-START)}
    versions={"python":platform.python_version(),"numpy":np.__version__,"pandas":pd.__version__,"scipy":scipy.__version__,"scikit-learn":sklearn.__version__,"matplotlib":matplotlib.__version__,"joblib":joblib.__version__}
    summary={"audit":audit,"model_selection":selection,"metrics":result.reset_index().to_dict("records"),"comparisons":comparisons,"importance":importance.to_dict("records"),"coefficients":coeff.to_dict("records"),"diagnostics":diagnostics,"versions":versions,"figures":FIGURES,"clipping":bounds,"subgroups":subgroup_rows}
    (OUT/"tables"/"analysis_summary.json").write_text(json.dumps(summary,indent=2))
    (OUT/"figures"/"figure_catalog.json").write_text(json.dumps(FIGURES,indent=2))
    (OUT/"code"/"requirements.txt").write_text("\n".join(f"{name}=={version}" for name,version in versions.items() if name!="python")+"\npython-docx==1.2.0\n")
    print("COMPLETE",json.dumps(summary["metrics"]),flush=True)
    print("Comparisons",json.dumps(comparisons),flush=True)
    print("Interpretation",importance.to_string(index=False),flush=True)
    print("Elapsed",time.perf_counter()-START,flush=True)


if __name__=="__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=SOURCE, help="Path to the source wallet_features.csv")
    SOURCE = parser.parse_args().data.resolve()
    with warnings.catch_warnings(record=True) as caught, threadpool_limits(limits=4):
        warnings.simplefilter("always")
        run()
        (OUT/".build"/"analysis_warnings.txt").write_text("\n".join(f"{w.category.__name__}: {w.message}" for w in caught))
