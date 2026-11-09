AGENT ?= claude-code
MODEL ?= claude-opus-5-5
TRIALS ?= 5
TASKS ?= all
VARIANTS ?= all
CONDITIONS ?= structured
PARALLEL ?= 3

.PHONY: build validate run replay test report zip viewer timings

build:
	python3 run.py build --tasks $(TASKS)

validate:
	python3 run.py validate --tasks $(TASKS)

run:
	python3 run.py run --agent $(AGENT) --model $(MODEL) --trials $(TRIALS) --tasks $(TASKS) --parallel $(PARALLEL) --variants $(VARIANTS) --conditions $(CONDITIONS)

replay:
	python3 -m grader.replay results/
	python3 -m report.metrics

test:
	python3 -m unittest discover -s tracer -t .
	python3 -m unittest discover -s grader -t .
	python3 -m unittest discover -s report -t .
	python3 scripts/test_build_viewer.py

report:
	python3 -m report
	python3 scripts/readme_fill.py

zip:
	bash scripts/make_zip.sh

viewer:
	python3 scripts/build_viewer.py

timings:
	bash scripts/timings.sh
