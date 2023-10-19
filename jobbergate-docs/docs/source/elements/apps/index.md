# Jobbergate Apps

Jobbergate consists of three interconnected Python applications that operate harmoniously. These applications enable the
creation and dispatch of Job Scripts to a Slurm cluster, eliminating the need for the Jobbergate user to engage directly
with Slurm – a process that might be challenging or unfeasible.

While the primary interface for user interaction with Jobbergate is the [CLI](./cli.md), both the [API](./api.md) and
[Core package](./core.md) can be employed to develop automation and craft tools leveraging Jobbergate's capabilities.

The three apps in Jobbergate are:

- [Jobbergate API](./api.md)
- [Jobbergate CLI](./cli.md)
- [Jobbergate Agent](./agent.md)

And the SDK that provides python integration is:

- [Jobbergate Core](./core.md)
