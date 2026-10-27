# Rebuild the market study from the committed sample (no raw data needed):
#   make market
# Rebuild everything from raw trades too (needs data/raw/wallet_trades/ locally):
#   make market-from-raw

PY ?= python3

.PHONY: market market-from-raw tables figures notebook

market: tables figures notebook

tables:
	$(PY) scripts/run_market_analysis.py > /dev/null

figures: tables
	$(PY) scripts/make_market_figures.py

notebook: figures
	cd notebooks && jupyter nbconvert --to notebook --execute --inplace 01_market_calibration.ipynb

market-from-raw:
	$(PY) scripts/build_market_sample.py
	$(MAKE) market
