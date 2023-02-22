import subprocess, time
from core.MongoCommand import MongoCommand
from core.ServerCommand import ServerCommand

DEBUG_MODE = True

class TCManager:
    def __init__(self, source_dbhome: str, target_dbhome: str, SID: str, SPW: str, TID: str, TPW: str):
        self.source_dbhome = source_dbhome # "/data/mongodb/"
        self.target_dbhome = target_dbhome # "/data/mongodb_backup/"
        self.source_id = SID
        self.source_pw = SPW
        self.target_id = TID
        self.target_pw = TPW

    def config_setting(self, source: str, target: str, shardinfo: dict, source_ns: str, target_ns: str, cluster: bool): # source and target are maybe mongos
        # if both source and target are shared cluster, "cluster" is true
        sourcemc = MongoCommand(source, self.source_id, self.source_pw) # source
        targetmc = MongoCommand(target, self.target_id, self.target_pw) # localhost

        if cluster and sourcemc.check_balancer(): 
            print("turn off the balancer in source")
            return True

        if cluster and targetmc.check_balancer(): 
            print("turn off the balancer in target")
            return True

        ixInfo, distInfo = sourcemc.get_collection_info(source_ns, cluster)
        targetmc.set_collection_info(ixInfo, target_ns, distInfo)

        if cluster:
            #lock
            targetmc.remove_chunk_info(target_ns) # need to backup??
            chunklist = sourcemc.find_chunk_info(source_ns)
            self.__update_config_meta(targetmc, shardinfo, target_ns, chunklist)

            targetmc.sync_epoch(target_ns)

        return False


    def shard_setting(self, source: str, target: str, source_ns: str, target_ns: str, start_command: str = None):
        # source and target are maybe mongos
        sourcemc = MongoCommand(source, self.source_id, self.source_pw)
        targetmc = MongoCommand(target, self.target_id, self.target_pw)

        source_sec = sourcemc.find_secondary()[0] # must be always the same member
        source_sec_mc = MongoCommand(source_sec, self.source_id, self.source_pw, True)
        source_addr = source_sec.split(":")[0] # the hostname of a secondary member

        scol_uri, six_uri = self.__get_meta_table(source_sec_mc, source_ns)
        # target_sec 0, 1..2

        for target_sec in targetmc.find_secondary():
            print(target_sec)
            # target_addr = target_sec.split(":")[0]
            self.__shard_setting_command(source_sec, target_sec, scol_uri, six_uri, target_ns, False, start_command)

        time.sleep(5)
        primary = targetmc.find_primary()
        # target_addr = primary.split(":")[0]

        self.__shard_setting_command(source_sec, primary, scol_uri, six_uri, target_ns, True, start_command)


    def matching_shards(self, config):
        matched_list=list()
        for source_shard, source_address in config["source_shardlist"].items():
            candi = None
            for key, val in config["couple_server"].items():
                if key == source_shard:
                    candi = val
                    break

            if candi:
                for target_shard, target_address in config["target_shardlist"].items():
                    if target_shard == candi:
                        tp = (source_address, target_address)
                        matched_list.append(tp)
                        break
        return matched_list


    def __update_config_meta(self, targetmc: MongoCommand, shardinfo: dict, target_ns: str, chunklist: list):
        input_list=list()
        for info in chunklist:
            del info["_id"] # remove _id to de-duplicate target has the same _id (unique index)
            info.update({"ns": target_ns, "shard": shardinfo[info["shard"]]})
            if info.get("history"):
                for history in info["history"]:
                    history.update({"shard": shardinfo[history["shard"]]})
            input_list.append(info)
            if len(input_list) > 1000:
                targetmc.insert_chunk_info(input_list)
                input_list.clear()
        if len(input_list) > 0: targetmc.insert_chunk_info(input_list)


    def __shard_setting_command(self, source: str, target: str,
                             scol_uri: str, six_uri: dict, namespace: str, stepdown: bool, start_command: str):
        target_addr = target.split(":")[0]
        self.__dist_util(target_addr)
        target_mc = MongoCommand(target, self.target_id, self.target_pw, True)
        tcol_uri, tix_uri = self.__get_meta_table(target_mc, namespace)

        print(scol_uri, six_uri, tcol_uri, tix_uri)
        self.__replaceCollection(source, target, scol_uri, six_uri, tcol_uri, tix_uri, namespace, stepdown, start_command)


    def __replaceCollection(self, source: str, target: str, scol_uri: str,
                           six_uri: dict, tcol_uri:str, tix_uri: dict,
                           namespace: str, primary: bool, start_command:str):
        target_wo_port = target.split(":")[0]
        source_addr = source.split(":")[0]

        sc = ServerCommand(target_wo_port)
        mc = MongoCommand(target, self.target_id, self.target_pw, True)
        source_mc = MongoCommand(source, self.source_id, self.source_pw, True)

        # sc.dependency()
        if primary: 
            mc.drop_cached_chunk(namespace) # In replicaset, this command is not needed. 
            mc.stepdown()
        try:
            mc.shutdown()
        except Exception as e:
            print("shutdown exception", str(e))

        # collection sync
        source_mc.fsync_lock() # lock
        sc.rsync(source_addr, self.source_dbhome, scol_uri, self.target_dbhome, tcol_uri)

        # index sync
        for k, idx in six_uri.items(): # number of sindex_uri == number of sindex_uri            
            sc.rsync(source_addr, self.source_dbhome, idx, self.target_dbhome, tix_uri[k])
        source_mc.fsync_unlock()

        sc.salvage(self.target_dbhome, tcol_uri)
        # index sync
        for k, idx in six_uri.items(): # number of sindex_uri == number of sindex_uri            
            sc.salvage(self.target_dbhome, tix_uri[k])
            
        sc.start(start_command)


    def __dist_util(self, hostname): #TODO
        subprocess.call(["rsync", "--bwlimit=100M", "-avz", "--no-perms", "-e", "ssh -o StrictHostKeyChecking=no", "util/wt", f"root@{hostname}:/tmp/"])
        # subprocess.call(["rsync", "--bwlimit=100M", "-avz", "--no-perms", "-e", "ssh -o StrictHostKeyChecking=no", "util/libzstd.so.1", f"root@{hostname}:/lib64/"])


    def __get_meta_table(self, mc:MongoCommand, namespace:str):
        index, _ = mc.get_collection_info(namespace, False)
        # remove statistics:table: prefix
        collstats = mc.collstats(namespace)
        index_uri = dict()
        col_uri = collstats["wiredTiger"]["uri"].replace("statistics:table:","")+".wt"
        for name in index:
            index_uri[name] = collstats["indexDetails"][name]["uri"].replace("statistics:table:","")+".wt"
        return col_uri, index_uri
