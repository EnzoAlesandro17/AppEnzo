import getpass

import click

from app.auth import services


@click.command("create-user")
@click.option("--email", prompt=True)
def create_user_command(email: str) -> None:
    password = getpass.getpass("Password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        click.echo("Passwords don't match")
        return
    try:
        user_id = services.create_user(email, password)
    except services.EmailAlreadyRegistered:
        click.echo(f"Email already registered: {email}")
        return
    click.echo(f"Created user {email} ({user_id})")
