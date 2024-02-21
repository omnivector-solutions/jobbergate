# JobProperties

Specialized model for job properties.  See more details at: https://slurm.schedmd.com/rest_api.html

## Properties
Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**account** | **object** | Charge resources used by this job to specified account. | [optional] 
**account_gather_frequency** | **object** | Define the job accounting and profiling sampling intervals. | [optional] 
**argv** | **object** | Arguments to the script. | [optional] 
**array** | **object** | Submit a job array, multiple jobs to be executed with identical parameters. The indexes specification identifies what array index values should be used. | [optional] 
**batch_features** | **object** | features required for batch script&#39;s node | [optional] 
**begin_time** | **object** | Submit the batch script to the Slurm controller immediately, like normal, but tell the controller to defer the allocation of the job until the specified time. | [optional] 
**burst_buffer** | **object** | Burst buffer specification. | [optional] 
**cluster_constraints** | **object** | Specifies features that a federated cluster must have to have a sibling job submitted to it. | [optional] 
**comment** | **object** | An arbitrary comment. | [optional] 
**constraints** | **object** | node features required by job. | [optional] 
**container** | **object** | Absolute path to OCI container bundle. | [optional] 
**core_specification** | **object** | Count of specialized threads per node reserved by the job for system operations and not used by the application. | [optional] 
**cores_per_socket** | **object** | Restrict node selection to nodes with at least the specified number of cores per socket. | [optional] 
**cpu_binding** | **object** | Cpu binding | [optional] 
**cpu_binding_hint** | **object** | Cpu binding hint | [optional] 
**cpu_frequency** | **object** | Request that job steps initiated by srun commands inside this sbatch script be run at some requested frequency if possible, on the CPUs selected for the step on the compute node(s). | [optional] 
**cpus_per_gpu** | **object** | Number of CPUs requested per allocated GPU. | [optional] 
**cpus_per_task** | **object** | Advise the Slurm controller that ensuing job steps will require ncpus number of processors per task. | [optional] 
**current_working_directory** | **object** | Instruct Slurm to connect the batch script&#39;s standard output directly to the file name. | [optional] 
**deadline** | **object** | Remove the job if no ending is possible before this deadline (start &gt; (deadline - time[-min])). | [optional] 
**delay_boot** | **object** | Do not reboot nodes in order to satisfied this job&#39;s feature specification if the job has been eligible to run for less than this time period. | [optional] 
**dependency** | **object** | Defer the start of this job until the specified dependencies have been satisfied completed. | [optional] 
**distribution** | **object** | Specify alternate distribution methods for remote processes. | [optional] 
**environment** | **Dict[str, object]** | Dictionary of environment entries. | [optional] 
**exclusive** | **object** | The job allocation can share nodes just other users with the &#39;user&#39; option or with the &#39;mcs&#39; option). | [optional] 
**get_user_environment** | **object** | Load new login environment for user on job node. | [optional] 
**gres** | **object** | Specifies a comma delimited list of generic consumable resources. | [optional] 
**gres_flags** | **object** | Specify generic resource task binding options. | [optional] 
**gpu_binding** | **object** | Requested binding of tasks to GPU. | [optional] 
**gpu_frequency** | **object** | Requested GPU frequency. | [optional] 
**gpus** | **object** | GPUs per job. | [optional] 
**gpus_per_node** | **object** | GPUs per node. | [optional] 
**gpus_per_socket** | **object** | GPUs per socket. | [optional] 
**gpus_per_task** | **object** | GPUs per task. | [optional] 
**hold** | **object** | Specify the job is to be submitted in a held state (priority of zero). | [optional] 
**kill_on_invalid_dependency** | **object** | If a job has an invalid dependency, then Slurm is to terminate it. | [optional] 
**licenses** | **object** | Specification of licenses (or other resources available on all nodes of the cluster) which must be allocated to this job. | [optional] 
**mail_type** | **object** | Notify user by email when certain event types occur. | [optional] 
**mail_user** | **object** | User to receive email notification of state changes as defined by mail_type. | [optional] 
**mcs_label** | **object** | This parameter is a group among the groups of the user. | [optional] 
**memory_binding** | **object** | Bind tasks to memory. | [optional] 
**memory_per_cpu** | **object** | Minimum real memory per cpu (MB). | [optional] 
**memory_per_gpu** | **object** | Minimum memory required per allocated GPU. | [optional] 
**memory_per_node** | **object** | Minimum real memory per node (MB). | [optional] 
**minimum_cpus_per_node** | **object** | Minimum number of CPUs per node. | [optional] 
**minimum_nodes** | **object** | If a range of node counts is given, prefer the smaller count. | [optional] 
**name** | **object** | Specify a name for the job allocation. | [optional] 
**nice** | **object** | Run the job with an adjusted scheduling priority within Slurm. | [optional] 
**no_kill** | **object** | Do not automatically terminate a job if one of the nodes it has been allocated fails. | [optional] 
**nodes** | **object** | Request that a minimum of nodes nodes and a maximum node count. | [optional] 
**open_mode** | **object** | Open the output and error files using append or truncate mode as specified. | [optional] 
**partition** | **object** | Request a specific partition for the resource allocation. | [optional] 
**priority** | **object** | Request a specific job priority. | [optional] 
**qos** | **object** | Request a quality of service for the job. | [optional] 
**requeue** | **object** | Specifies that the batch job should eligible to being requeue. | [optional] 
**reservation** | **object** | Allocate resources for the job from the named reservation. | [optional] 
**signal** | **object** | When a job is within sig_time seconds of its end time, send it the signal sig_num. | [optional] 
**sockets_per_node** | **object** | Restrict node selection to nodes with at least the specified number of sockets. | [optional] 
**spread_job** | **object** | Spread the job allocation over as many nodes as possible and attempt to evenly distribute tasks across the allocated nodes. | [optional] 
**standard_error** | **object** | Instruct Slurm to connect the batch script&#39;s standard error directly to the file name. | [optional] 
**standard_input** | **object** | Instruct Slurm to connect the batch script&#39;s standard input directly to the file name specified. | [optional] 
**standard_output** | **object** | Instruct Slurm to connect the batch script&#39;s standard output directly to the file name. | [optional] 
**tasks** | **object** | Advises the Slurm controller that job steps run within the allocation will launch a maximum of number tasks and to provide for sufficient resources. | [optional] 
**tasks_per_core** | **object** | Request the maximum ntasks be invoked on each core. | [optional] 
**tasks_per_node** | **object** | Request the maximum ntasks be invoked on each node. | [optional] 
**tasks_per_socket** | **object** | Request the maximum ntasks be invoked on each socket. | [optional] 
**thread_specification** | **object** | Count of specialized threads per node reserved by the job for system operations and not used by the application. | [optional] 
**threads_per_core** | **object** | Restrict node selection to nodes with at least the specified number of threads per core. | [optional] 
**time_limit** | **object** | Step time limit. | [optional] 
**time_minimum** | **object** | Minimum run time in minutes. | [optional] 
**wait_all_nodes** | **object** | Do not begin execution until all nodes are ready for use. | [optional] 
**wckey** | **object** | Specify wckey to be used with job. | [optional] 

## Example

```python
from openapi_client.models.job_properties import JobProperties

# TODO update the JSON string below
json = "{}"
# create an instance of JobProperties from a JSON string
job_properties_instance = JobProperties.from_json(json)
# print the JSON string representation of the object
print JobProperties.to_json()

# convert the object into a dict
job_properties_dict = job_properties_instance.to_dict()
# create an instance of JobProperties from a dict
job_properties_form_dict = job_properties.from_dict(job_properties_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


