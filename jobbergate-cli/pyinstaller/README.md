# Proof of concept: Create a bundle for jobbergate-cli and all its dependencies

* It is related to the ticket: [Create a proof of concept that creates a job-submission via Catia VB code plugin](https://jira.scania.com/browse/ASP-3101)
* This is based on PyInstaller, see [PyInstaller documentation](https://pyinstaller.readthedocs.io/en/stable/index.html).

## How to use

* Create a virtual environment, any approach for this should be fine. I'm using conda on my Windows machine:

```bash
conda create --name ASP-3101-jobbergate-cli python=3.10
```

```bash
conda activate ASP-3101-jobbergate-cli
```

* Install jobbergate-cli and its dependencies in this virtual environment:

```bash
python -m pip install -e .
```

* Install PyInstaller in this virtual environment:

```bash
python -m pip install pyinstaller==5.9.0
```

* Change the working directory to the `pyinstaller` folder:

```bash
cd pyinstaller
```

* Create the `.env` file for the staging environment.

* Create the bundle for jobbargate-cli using PyInstaller:

```bash
pyinstaller jobbergate.spec
```

* The bundle will be created in the `dist` folder, and it will contain the executable `jobbergate.exe`. Compress the folder into a zip file to facilitate the distribution:

```bash
powershell Compress-Archive -LiteralPath 'dist\jobbergate' -DestinationPath "jobbergate.zip"
```

* Test the bundle:

```bash
cd dist\jobbergate
.\jobbergate.exe --help
.\jobbergate.exe login
.\jobbergate.exe list-applications
```