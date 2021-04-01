"""
Script used to create super users via click
"""
import asyncio

import click

import jobbergateapi2.main as main
from jobbergateapi2.apps.users.models import User
from jobbergateapi2.apps.users.schemas import pwd_context
from jobbergateapi2.config import settings


async def create_super_user(username, email, password):
    """
    Async function to connect async with the database and create the super user
    """
    await main.db.set_bind(settings.DATABASE_URL)
    await User.create(username=username, email=email, is_active=True, password=password, is_admin=True)


@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
@click.option("--email", prompt=True)
@click.option("--username", prompt=True)
@click.command()
def createsuperuser(username, email, password):
    """
    Click command for creating super users in the database
    """
    password = pwd_context.hash(password)
    asyncio.run(create_super_user(username, email, password))
    click.echo(f"User {username} created")
