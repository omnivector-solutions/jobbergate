test:
	poetry run pytest -v

lint:
	poetry run pre-commit run -a -v

format:
	poetry run pre-commit run -a -v isort
	poetry run pre-commit run -a -v black

install:
	poetry install

run:
	poetry run uvicorn --host 0.0.0.0 jobbergateapi2.main:app --reload

createsuperuser:
	poetry run createsuperuser

update-precommit:
	poetry run pre-commit autoupdate

clean: clean-eggs clean-build
	@find . -iname '*.pyc' -delete
	@find . -iname '*.pyo' -delete
	@find . -iname '*~' -delete
	@find . -iname '*.swp' -delete
	@find . -iname '__pycache__' -delete
	@rm -rf .tox

clean-eggs:
	@find . -name '*.egg' -print0|xargs -0 rm -rf --
	@rm -rf .eggs/

clean-build:
	@rm -fr build/
	@rm -fr dist/
	@rm -fr *.egg-info
