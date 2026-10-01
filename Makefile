export DBT_PROFILES_DIR := $(CURDIR)
DBT := uv run dbt

.PHONY: setup redis-up redis-down driver data deps debug seed load run test build incremental-demo docs docs-serve clean all

## One-time setup: Python env, driver, data, Redis
setup: deps driver data redis-up

deps:
	uv sync

driver:
	./scripts/build_driver.sh

data:
	./scripts/download_data.sh

redis-up:
	docker compose up --detach --wait redis

redis-down:
	docker compose down

## dbt commands
debug:
	$(DBT) debug

seed:
	$(DBT) seed

# Load the raw trips CSV (every 50th row by default; override with ARGS, e.g.
# make load ARGS="--args '{sample_every: 10}'")
load:
	$(DBT) run-operation load_raw_trips $(ARGS)

run:
	$(DBT) run

test:
	$(DBT) test

build:
	$(DBT) build

# fct_trips with the first half of January, then an incremental run that
# reloads the last day and appends the rest.
incremental-demo:
	$(DBT) run -s +fct_trips --full-refresh --vars '{trips_end: "2019-01-16 00:00:00"}'
	$(DBT) show --inline "select count(*) as trips, max(pickup_datetime) as last_pickup from {{ ref('fct_trips') }}" --vars '{trips_end: "2019-01-16 00:00:00"}'
	$(DBT) run -s +fct_trips
	$(DBT) show --inline "select count(*) as trips, max(pickup_datetime) as last_pickup from {{ ref('fct_trips') }}"

docs:
	$(DBT) docs generate

docs-serve: docs
	$(DBT) docs serve

clean:
	$(DBT) clean

## Everything, from an empty Redis
all: debug seed load build docs
