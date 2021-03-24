import asyncio

import click

from jobbergate_api.main import db
from jobbergate_api.apps.users.models import User
from jobbergate_api.apps.users.schemas import pwd_context
from jobbergate_api.config import settings


@click.group()
def cli():
    pass


async def create_super_user(username, email, password):
    await db.set_bind(settings.DATABASE_URL)
    await User.create(username=username, email=email, is_active=True, password=password, is_admin=True)


@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
@click.option("--email", prompt=True)
@click.option("--username", prompt=True)
@click.command()
def createsuperuser(username, email, password):
    password = pwd_context.hash(password)
    asyncio.run(create_super_user(username, email, password))
    click.echo(f"User {username} created")


cli.add_command(createsuperuser)

if __name__ == "__main__":
    cli()
