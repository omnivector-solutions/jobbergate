from jobbergate_cli.end_to_end_testing.applications import Applications
from jobbergate_cli.end_to_end_testing.constants import TEST_APPLICATIONS_PATH


def main():

    applications = Applications(
        entity_list=[p for p in TEST_APPLICATIONS_PATH.iterdir() if p.is_dir()],
    )

    applications.create()
    applications.get()
    applications.list()
    print("main")


if __name__ == "__main__":
    main()
