# TC-Kubernetes

## Image

TCM: https://hub.docker.com/r/officialkakao/tcm

TCA: https://hub.docker.com/r/officialkakao/tca

## Usage

TC is portable for every MongoDB chart for kubernetes.
We confirmed that TC can be plugged into [bitnami-mongodb](https://github.com/bitnami/charts/tree/main/bitnami/mongodb/)

WARN: If the TC process crashes during the runtime, TCM must be restarted.

### Execution

### 1. Create ssh key and copy to source
To send data, you must set ssh passwordless login between source and target.

```
kubectl create secret generic ssh-key-secret --from-file=id_rsa=.ssh/id_rsa --from-file=id_rsa.pub=.ssh/id_rsa.pub
```

### 2. Add TCA to the chart
Specify an init container with TC image in the bitnami-mongodb chart.
[initContainer](https://github.com/bitnami/charts/blob/main/bitnami/mongodb-sharded/values.yaml#L1093)
Also, add the volume and mount in the chart.


```    
initContainers:
   - name: tca-app
     image: $(image_name)
     imagePullPolicy: Always
     env:
     - name: TCM_URL
       value: $(url or IP)
     - name: SOURCE_ID
       value: $(mongodb_source_id)
     - name: SOURCE_PW
       value: $(mongodb_source_pw)
     volumeMounts:
     - name: secret-volume
       readOnly: true
       mountPath: /run/secrets/.ssh
     - name: datadir
       mountPath: $(shardsvr.persistence.mountPath)

    extraVolumes:
      - name: secret-volume
        secret:
          secretName: ssh-key-secret
          defaultMode: 0400
```


### 3. Write a chart for TCM and deploy it

Please refer to the example chart (tcm.yaml)

**1. sharded cluster**

There are six sections.  
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

[db_home]:

Keys are MongoDB's home path in source.
Values are MongoDB's home path in target.

Example)
```
apiVersion: v1
kind: ConfigMap
metadata:
  name: tc-meta
  namespace: default
data:
  meta.ini: |
    [connection_string]
    mongos_source_hostname:port=mongos_target_hostname:port


    [source_shardlist]
    source_shard_name1=source_shard1_hostname1:port,source_shard1_hostname2:port,source_shard1_hostname3:port
    source_shard_name2=source_shard2_hostname1:port,source_shard2_hostname2:port,source_shard2_hostname3:port
    
    [target_shardlist]
    target_shard_name1(pod_prefix)=target_shard1_hostname1(pod_name):port,target_shard1_hostname2(pod_name):port,target_shard1_hostname3(pod_name):port
    target_shard_name2(pod_prefix)=target_shard2_hostname1(pod_name):port,source_shard2_hostname2(pod_name):port,target_shard2_hostname3(pod_name):port
   
    [couple_server]
    source_shard_name1=target_shard_name1
    source_shard_name2=target_shard_name2

    [namespace]
    source_namespace1=target_namespace1
    source_namespace2=target_namespace2

    [db_home]
    /source/dbpath/ = /target/dbpath/

```

**2. Get the bearer token for a kubernetes cluster and edit env in the tcm chart**


$ kubectl get secret -n kube-system | grep dkos

Using the namespace and name from the above result, get the token as the following command:

$ kubectl describe secret -n kube-system dkos-token-abcde

According to the kubernetes cluster's configuration, modify "kube-system" and "dkos" above the command.


```
        - name: K8S_HOST
          value: $(https://hostname:6443)
        - name: K8S_TOKEN
          value: $(dkos-token-abcde.TOKEN)
```

**3. deploy tcm**

kubectl apply -f tcm.yaml


### 4. Deploy MongoDB
helm install mongo /home/deploy/mongo-sharded-chart --set shards=2 --set shardsvr.dataNode.replicas=2 --set configsvr.replicas=3 --set mongos.replicas=2 --set shardsvr.arbiter.replicas=1 --set mongos.useStatefulSet=true --set mongos.servicePerReplica.enabled=true --set mongos.servicePerReplica.port=30000 

### 5. Call TCM to start copy data

curl http://TCM_URL:PORT or TCM_IP:PORT/
