test:
	poetry run pytest -v

lint:
	poetry run pre-commit run -a -v

install:
	poetry install

migrate:
	poetry run alembic upgrade head

run:
	poetry run uvicorn jobbergateapi2.main:app --reload

createsuperuser:
	poetry run python -m jobbergateapi2.utils createsuperuser

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
