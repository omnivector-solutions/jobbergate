> An [Omnivector](https://www.omnivector.io/) initiative
>
> [![omnivector-logo](https://omnivector-public-assets.s3.us-west-2.amazonaws.com/branding/omnivector-logo-text-black-horz.png)](https://www.omnivector.io/)


# Jobbergate Documentation

This repository contains the source for the Jobbergate Documentation page.

It is built using [MkDocs](https://www.mkdocs.org/).


## Build the Docs

To build the documentation static site, run the following command:

```bash
make docs
```


To view the rendered documentation locally, run:

```bash
make docs-serve
```


## Other Commands

To lint the python files in the `src` directory, run:

```bash
make lint
```


To clean up build artifacts, run:

```bash
make clean
```
