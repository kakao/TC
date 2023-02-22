# Transportable Collections (TC)
In a distributed environment, it is non-trivial to copy data between clusters. 
One of the fastest ways is to transfer data physically (e.g., physical backup).

We implement TC, a method to copy data between clusters, especially for MongoDB.

Basically, TC is implemented for a shareded cluster, but it can copy collections
 - **from a sharded cluster to shared clusters**
 - from a shareded cluster to replicasets
 - from a shareded cluster to standalones
 - from a replicaset (standalone) to replicasets
 - from a replicaset (standalone) to standalones

There are several use cases:

- Migration: physically migrate collections to other sharded clusters.
- Backup: need to back up only couple of collections.
- Database recovery: a database system is in a crash but collection files are alive.
- Assemble collections: copy a distributed collection in a sharded cluster and assemble them into a replicaset or a standalone.


## Limitations
There are limitations, which other systems are suffered too

> The same system (big endian vs. little endian)  
> Cold backup, i.e., do not change the state of a collection

If you need to use TC in online, consider the LVM snapshot.

Data consistency between shards is not guaranteed. 
To get consistent state for all shards, you must synchronize them by **oplog** from a source cluster.

## License

This software is licensed under the [Apache 2 license](LICENSE), quoted below.

Copyright 2023 Kakao Corp. <http://www.kakaocorp.com>

Licensed under the Apache License, Version 2.0 (the "License"); you may not
use this project except in compliance with the License. You may obtain a copy
of the License at http://www.apache.org/licenses/LICENSE-2.0.

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations under
the License.
