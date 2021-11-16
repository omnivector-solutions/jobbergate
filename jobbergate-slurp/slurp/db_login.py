def login(is_legacy=False):
    subprocess.run(["pgcli", settings.DATABASE_URL])

def main():
    typer.run(login)
