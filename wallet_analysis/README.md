# Wallet purchase price research

This study predicts `avg_buy_price` from six wallet characteristics. It excludes the `confirmed` flag throughout and retains all 55,952 wallets. The comparison uses a fixed 80 percent training and 20 percent test split, with five-fold validation inside training.

The primary models are a training-mean baseline, linear regression, and histogram gradient boosting. Test MAE is 22.14, 19.78, and 16.74 cents per share, respectively. Gradient boosting reduces MAE by 15.4 percent relative to linear regression. Its test R squared is 0.368. These are predictions across wallets using summaries from the same observed trading history. They do not establish future forecasting ability, profitability, or causal effects.

## Main deliverables

- `outputs/wallet_purchase_price_report.pdf` is the comprehensive 16-page report.
- `outputs/wallet_purchase_price_report.docx` is the editable report. HTML and Markdown versions are also included in `outputs/`.
- `outputs/wallet_purchase_price_slides.pptx` contains exactly four editable content slides: question and data, approach, results, and interpretation. It includes speaker notes and editable charts.
- `outputs/presentation_notes.md` contains the speaker notes and source references.
- `outputs/figure_gallery.html` displays all 15 figures in one self-contained page.
- `data/wallet_features.csv` is the source dataset.
- `figures/` contains the separate PNG and SVG versions, plus their caption catalog.
- `tables/` contains audit results, model selection, metrics, intervals, prediction records, and chart data.
- `models/` contains fitted estimators for the recorded Python package versions.
- `code/` contains the analysis and artifact authoring sources, plus the Python requirements.

## Reproduction

From the `wallet_analysis/` project directory, use Python 3.12 and install the recorded packages in a dedicated environment:

```sh
python3 -m pip install -r code/requirements.txt
python3 code/analyze_wallet_prices.py
```

The script defaults to `data/wallet_features.csv`. For a different source location, pass `--data '/path/to/wallet_features.csv'`. The recorded source SHA256 is `0a44686df51dc86a6f569e2f85867e6607f33bedffa521831b4767cbb8135c8a`.

The script checks the selected variables, creates the fixed split, saves training-only exploratory figures, selects boosting settings with training folds, and evaluates the fixed test set. It then produces the saved diagnostics, sensitivity models, and fitted estimators. Its usecols excludes the flag. No model choices follow the final test diagnostics.

Uncertainty intervals use 2,000 paired bootstrap samples of test wallets. Feature importance uses 20 shuffles per predictor. The report explains the assumptions, the activity-only sensitivity analysis, the alternative median baseline, and the limits of interpreting correlated predictors.

The report source can be rebuilt with `python3 code/build_report.py` after running the analysis. It reads `tables/` and `figures/` and writes the Word, HTML, Markdown, and gallery files to `outputs/`. The slide authoring module uses the first-party Artifact Tool presentation interface. The packaged PowerPoint file and live presentation are the finished deck.
