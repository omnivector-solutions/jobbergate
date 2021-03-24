test:
	poetry run pytest -v

lint:
	poetry run pre-commit run -a -v

install:
	poetry install

migrate:
	poetry run alembic upgrade head

run:
	poetry run uvicorn jobbergate_api.main:app --reload

createsuperuser:
	poetry run python -m jobbergate_api.utils createsuperuser

clean: clean-eggs clean-build
	@find . -iname '*.pyc' -delete
	@find . -iname '*.pyo' -delete
	@find . -iname '*~' -delete
	@find . -iname '*.swp' -delete
	@find . -iname '__pycache__' -delete

clean-eggs:
	@find . -name '*.egg' -print0|xargs -0 rm -rf --
	@rm -rf .eggs/

clean-build:
	@rm -fr build/
	@rm -fr dist/
	@rm -fr *.egg-info
