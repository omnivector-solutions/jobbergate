"""
Script used to create super users via click
"""
import asyncio

import click

from jobbergateapi2 import storage
from jobbergateapi2.apps.users.models import users_table
from jobbergateapi2.apps.users.schemas import pwd_context
from jobbergateapi2.compat import INTEGRITY_CHECK_EXCEPTIONS
from jobbergateapi2.main import init_database
from jobbergateapi2.storage import database


async def create_super_user(full_name, email, password):
    """
    Async function to connect async with the database and create the super user.
    """
    await init_database()
    query = users_table.insert()
    values = {
        "full_name": full_name,
        "email": email,
        "password": password,
        "is_superuser": True,
        "is_active": True,
        "principals": "role:admin",
    }
    async with database.transaction():
        try:
            await storage.database.execute(query=query, values=values)
        except INTEGRITY_CHECK_EXCEPTIONS:
            click.echo(f"User {full_name} already exists")
            return
    click.echo(f"User {full_name} created")


@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
@click.option("--email", prompt=True)
@click.option("--full-name", "full_name", prompt=True)
@click.command()
def createsuperuser(full_name, email, password):
    """
    Click command for creating super users in the database.
    """
    password = pwd_context.hash(password)
    asyncio.run(create_super_user(full_name, email, password))
