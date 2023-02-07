from jobbergate_cli.end_to_end_testing.applications import Applications
from jobbergate_cli.end_to_end_testing.job_scripts import JobScripts
from jobbergate_cli.end_to_end_testing.job_submission import JobSubmissions


def main():

    entity_list = [Applications(), JobScripts(), JobSubmissions()]

    for entity in entity_list:

        entity.create()
        entity.get()
        entity.list()


if __name__ == "__main__":
    main()
