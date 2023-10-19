!!! example "An [Omnivector](https://www.omnivector.io/){:target="\_blank"} initiative"

    [![omnivector-logo](https://omnivector-public-assets.s3.us-west-2.amazonaws.com/branding/omnivector-logo-text-black-horz.png)](https://www.omnivector.io/){:target="_blank"}

# Jobbergate Documentation

The following documentation provides a comprehensive overview of the Jobbergate system, detailing its purpose,
installation process, and operational guidelines.

Jobbergate serves as an advanced job templating and submission system, designed to seamlessly integrate with Slurm. This
integration facilitates the efficient re-use and remote submission of job scripts to a Slurm cluster.

At the heart of Jobbergate is its API, which acts as the pivotal control center for the entire system. This API
interacts with an agent positioned alongside a Slurm cluster. This agent is responsible for establishing communication
between both the Jobbergate API and the Slurm RESTful API. Furthermore, Jobbergate offers a Command Line Interface (CLI)
to ensure users have an intuitive means of interacting with the system.

Given that the API is cloud-based, users are granted the capability to modify jobs, dispatch them to affiliated clusters,
and oversee their progress from any device with internet connectivity.

Additionally, Jobbergate introduces a Python SDK named "Jobbergate Core". This SDK is equipped with tools tailored for
automation and can be effortlessly integrated into any Python-based project.
