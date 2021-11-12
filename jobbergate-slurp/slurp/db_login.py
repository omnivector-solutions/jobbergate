def login(is_legacy=typer.):
    subprocess.run(["pgcli", settings.DATABASE_URL])

def main():
    typer.run(login)
