.PHONY: install lint test de features train evaluate score app dbt-build dbt-docs clean

PY := python
KEDRO := kedro

install:
	pip install -r requirements-dev.txt
	pip install -e src

lint:
	isort --check-only src tests
	black --check src tests
	flake8 src tests

test:
	pytest --cov=src/meridian --cov-report=term-missing

de:
	$(KEDRO) run --pipeline de

features:
	$(KEDRO) run --pipeline fe

train:
	$(KEDRO) run --pipeline train

evaluate:
	$(KEDRO) run --pipeline eval

score:
	$(KEDRO) run --pipeline scoring

app:
	streamlit run app/meridian_app.py --server.port 8501

dbt-build:
	cd dbt && dbt seed --profiles-dir . && dbt snapshot --profiles-dir . && dbt run --profiles-dir . && dbt test --profiles-dir .

dbt-docs:
	cd dbt && dbt docs generate --profiles-dir . && dbt docs serve --profiles-dir . --port 8081

clean:
	rm -rf data/02_intermediate/* data/03_primary/* data/04_feature/* data/05_model_input/*
	rm -rf data/06_models/* data/07_model_output/* data/08_reporting/*
	find . -name "__pycache__" -type d -exec rm -rf {} +
