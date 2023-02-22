import sys, requests
import argparse, configparser
from core.TCManager import TCManager
from multiprocessing import Process
import threading, time

#-----------REQUIREMENT--------------#
# Each shard must contain the corresponding collection
# The id / password must be the same in mongos and mongod (difficult to set)
# source id_rsa, target: authorized_keys


def main(parse):
    config = configparser.ConfigParser(delimiters='=')
    config.read(parse.file)
    shardinfo = dict()

    source_home = None
    target_home = None

    source_url = None
    target_url = None

    source_id = parse.source_id
    source_pw = parse.source_pw
    target_id = parse.target_id
    target_pw = parse.target_pw

    # ------------ sync config meta for a sharded cluster ---------- #
    for key, val in config["couple_server"].items():
        shardinfo[key] = val

    for src, target in config["db_home"].items():
        source_home = src
        target_home = target

    #TODO: add fsync_lock, add fsync_unlock, check balancer state, other versions such as cluster -> repl and repl -> repl
    # ------------ for each namespace ---------- #
    for src, target in config["connection_string"].items():
        source_url = src
        target_url = target

    tc = TCManager(source_home, target_home, source_id, source_pw, target_id, target_pw)
    start_command = None
    if config.get("mongod_start", "cmd"):
        start_command = config["mongod_start"]["cmd"]


    # before execution, check that the target collection is empty
    for source_ns, target_ns in config["namespace"].items():
        print("collection", source_ns, target_ns)
        threads = [] # multi-thread

        balancer = False
        if parse.source_type == "cluster" and parse.target_type == "cluster":
            balancer = tc.config_setting(source_url, target_url, shardinfo, source_ns, target_ns, True)
        elif parse.source_type == "cluster" and parse.target_type == "replicaset":
            balancer = tc.config_setting(source_url, target_url, shardinfo, source_ns, target_ns, False)
        elif parse.source_type == "replicaset" and parse.target_type == "replicaset":
            balancer = tc.config_setting(source_url, target_url, shardinfo, source_ns, target_ns, False)
        else:
            print("TC does not allow the option")
            return

        if balancer: return

        for source_addr, target_addr in tc.matching_shards(config):
            th=threading.Thread(target=tc.shard_setting, args=(source_addr, target_addr, source_ns, target_ns, start_command, ))
            th.start()
            threads.append(th)

        for t in threads:
            t.join()
            # tc.shard_setting(source_addr, target_addr, source_ns, target_ns, start_command)
        time.sleep(10)


if __name__=="__main__":
    DEBUG_MODE = True

    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--source_type", help="cluster, replicaset", default="cluster")
    parser.add_argument("-t", "--target_type", help="cluster, replicaset", default="cluster")
    parser.add_argument("-f", "--file", help="metafile", default="meta.ini")
    parser.add_argument("--source_id", help="Source user name")
    parser.add_argument("--source_pw", help="Source password")
    parser.add_argument("--target_id", help="Target user name")
    parser.add_argument("--target_pw", help="Target password")
    pres = parser.parse_args()

    if pres.source_type == "replicaset" and pres.target_type == "cluster":
        print("TC does not allow the option")
        exit(1)
    main(pres)
