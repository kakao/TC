# Transportable Collections (TC)

This version is for the bare-metal system.

## Environment
Centos7  
python3.6 or later

## Pre-requisites
You must set up the ssh without password between the TC server and target servers to give commands remotely, and between source and target servers for *rsync*.

TC connects target servers as *root* so that the *root* has ownership to start mongod

### Dependency
rsync
pymongo
requests
paramiko

## Install
[wt](https://github.com/wiredtiger/wiredtiger/tree/develop/cmake)

You must install [WiredTiger](https://source.wiredtiger.com/develop/build-posix.html). 

After build the utility successfully, you need to copy *wt* in the util folder (bare-metal/util)

If the data are compressed by snappy, zstd, or zlib, you must install libraries to each machine in advance. (e.g, in centos, yum install snappy-devel libzstd-devel zlib-devel).

```
pip3 install -r requirements.txt
```

After build it successfully, you must copy it in the *util* folder.

## Usage

### Execution

**python3 main.py -s cluster -t cluster**

> * -s, --source_type : cluster, replicaset  
> * -t, --target_type : cluster, replicaset 
> * --source_id : Source user name
> * --source_pw : Source password
> * --target_id : Target user name
> * --target_pw : Target password

Note that TC does not allow "-s replicaset -t cluster"

### Write meta.ini

**1. sharded cluster**

There are five sections.  
delimeter : "="  

[connection_string]:  
Key is source hostname (fqdn) and source port.  
Value is target hostname (fqdn) and target port.

[source_shardlist]:  
Keys are source shard names, which must be the same as keys the coule_server section below.  
Values are source shard hostnames and their ports.

[target_shardlist]:  
Keys are target shard names, which must be the same as values the coule_server section below.  
Values are target shard hostnames and their ports.

[couple_server]:
Keys are source shard names, which are same as the name in the *source_shardlist* section.  
Values are target shard names, which are same as the name in the *target_shardlist* section.

[namespace]:
Keys are namespaces of source.
Values are namespaces of target.

[mongod_start]:  
The command to start mongod in target servers 

Example)
```
[connection_string]
mongos_source_hostname:port=mongos_target_hostname:port

[source_shardlist]
source_shard_name1=source_shard1_hostname1:port,source_shard1_hostname2:port,source_shard1_hostname3:port
source_shard_name2=source_shard2_hostname1:port,source_shard2_hostname2:port,source_shard2_hostname3:port
...

[target_shardlist]
target_shard_name1=target_shard1_hostname1:port,target_shard1_hostname2:port,target_shard1_hostname3:port
target_shard_name2=target_shard2_hostname1:port,source_shard2_hostname2:port,target_shard2_hostname3:port
...

[couple_server]
source_shard_name1=target_shard_name1
source_shard_name2=target_shard_name2
...

[namespace]
source_namespace1=target_namespace1
source_namespace2=target_namespace2
...

[mongod_start]
cmd="/usr/bin/mongod -f /etc/mongod.conf"

[db_home]
/source/path/to/mongodb = /target/path/to/mongodb
```
