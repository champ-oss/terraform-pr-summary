coverage:
	pip3 install coverage pytest
	coverage run -m pytest --ignore=glue
	coverage html --omit="test_*.py"
	coverage xml --omit="test_*.py"
	open htmlcov/index.html || true

check-coverage:
	pip3 install coverage pytest
	coverage run -m pytest --ignore=glue
	coverage xml --omit="test_*.py"
	coverage report --fail-under=80

lint:
	pip3 install flake8
	flake8 --exclude=venv/,terraform/ --max-line-length=130 .

test:
	pip3 install coverage pytest
	coverage run -m pytest --log-cli-level=INFO

