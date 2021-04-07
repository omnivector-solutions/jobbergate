"""
Script used to create super users via click
"""
import asyncio

import click

from jobbergateapi2 import storage
from jobbergateapi2.apps.users.models import users_table
from jobbergateapi2.apps.users.schemas import pwd_context
from jobbergateapi2.main import disconnect_database, init_database


async def create_super_user(username, email, password):
    """
    Async function to connect async with the database and create the super user
    """
    await init_database()
    query = users_table.insert()
    values = {"username": username, "email": email, "password": password, "is_admin": True}
    await storage.database.execute(query=query, values=values)
    await disconnect_database()


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
