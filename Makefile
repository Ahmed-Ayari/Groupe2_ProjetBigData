# Usage: make <target>. Set PY=python3 if needed. Smoke targets use configs/smoke.yaml (synthetic data).
PY ?= python
MAX_FILES ?= 500
export PYTHONPATH := src

.PHONY: setup env test smoke audit lots pilot grid sizeup-cal fit sizeup-test final evaluate mining plots facts package purge-raw ukdale-debug all

setup:
	$(PY) -m pip install -r requirements.txt
env:
	$(PY) -m bigdata.runner --env
test:
	BIGDATA_CONFIG=configs/smoke.yaml $(PY) -m pytest tests -q
smoke:
	BIGDATA_CONFIG=configs/smoke.yaml $(PY) scripts/make_smoke_data.py
	BIGDATA_CONFIG=configs/smoke.yaml $(PY) -m bigdata.campaign pilot --lot cal_1
	BIGDATA_CONFIG=configs/smoke.yaml $(PY) -m bigdata.campaign grid --lot cal_2
	BIGDATA_CONFIG=configs/smoke.yaml $(PY) -m bigdata.campaign sizeup-cal --P 16
	BIGDATA_CONFIG=configs/smoke.yaml $(PY) -m bigdata.selector fit
	BIGDATA_CONFIG=configs/smoke.yaml $(PY) -m bigdata.campaign final
	BIGDATA_CONFIG=configs/smoke.yaml $(PY) -m bigdata.selector evaluate
# ---- real data (long; run them yourself, see README) ----
metropt:
	$(PY) -m bigdata.acquire metropt && $(PY) -m bigdata.audit && $(PY) -m bigdata.prepare metropt
weeks_list:
	@echo "Start with one week: make ukdale-list WEEKS=\"2013/wk11\""
ukdale-list:
	$(PY) -m bigdata.acquire ukdale-list $(if $(WEEKS),--weeks $(WEEKS),) $(if $(FILELIST),--filelist $(FILELIST),) --max-files $(MAX_FILES)
ukdale-debug:
	$(PY) -m bigdata.acquire ukdale-debug --week $(WEEK)
lots:
	$(PY) -m bigdata.lots
download:
	$(PY) -m bigdata.acquire ukdale-download --lots cal_1 cal_2 cal_3 test_1 test_2 test_3
pilot:
	$(PY) -m bigdata.campaign pilot && $(PY) -m bigdata.diagnose
grid:
	$(PY) -m bigdata.campaign grid --lot cal_2
	$(PY) -m bigdata.campaign grid --lot cal_1
sizeup-cal:
	$(PY) -m bigdata.campaign sizeup-cal --P $(P)
fit:
	$(PY) -m bigdata.selector fit
final:
	$(PY) -m bigdata.campaign final
evaluate:
	$(PY) -m bigdata.selector evaluate
mining:
	$(PY) -m bigdata.mining
plots:
	$(PY) -m bigdata.plots && $(PY) -m bigdata.report_facts
package:
	$(PY) scripts/package.py
purge-raw:
	@echo "Delete data/raw/ukdale/house_1 manually once all runs are finished (prepared Parquet is kept)."
