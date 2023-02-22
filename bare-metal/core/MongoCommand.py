from pymongo import MongoClient
import pymongo


class MongoCommand:
    def __init__(self, conn_string, ID, PW, dc=False):
        self.client = MongoClient(conn_string, username=ID, password=PW, directConnection=dc)

    def find_chunk_info(self, namespace: str):
        database = self.client["config"]
        coll = database["chunks"]
        return coll.find({"ns":namespace})

    def insert_chunk_info(self, data: list):
        database = self.client["config"]
        coll = database["chunks"]
        coll.insert_many(data)

    def remove_chunk_info(self, namespace: str):
        database = self.client["config"]
        coll = database["chunks"]
        coll.delete_many({"ns":namespace})

    def fsync_lock(self):#: tuple[str, str]):
        db = self.client.admin
        db.command({'fsync':1, 'lock':True})

    def fsync_unlock(self):#: tuple[str, str]):
        db = self.client.admin
        db.command({'fsyncUnlock':1})

    def check_balancer(self):#: tuple[str, str]):
        x = self.client["config"]["settings"].find_one({"_id": "balancer"})
        if x and x.get("stopped"): return not x["stopped"]
        else: return True

    def drop_cached_chunk(self, namespace: str):
        database = self.client["config"]
        coll = database[f"cache.chunks.{namespace}"]
        coll.drop()

    def sync_epoch(self, namespace:str):
        database = self.client["config"]
        coll = database["chunks"]
        collection = database["collections"]
        lastmodEpoch = collection.find_one({"_id":namespace},{"lastmodEpoch": 1, "_id":0})["lastmodEpoch"]
        coll.update_many({"ns": namespace}, {"$set":{"lastmodEpoch": lastmodEpoch}})

    def get_collection_info(self, namespace:str, cluster:bool = True):
        dbcol=namespace.split(".")
        target_database = self.client[dbcol[0]]
        target_coll=target_database[dbcol[1]]
        indexInfo = target_coll.index_information()

        dist_method_info=None
        if cluster:
            database = self.client["config"]
            coll = database["collections"]
            dist_method_info = coll.find_one({"_id":namespace}, {"_id":0, "key":1})

        return indexInfo, dist_method_info

    def set_collection_info(self, collIndex:list, namespace:str, dist_method_info=dict):
        dbcol=namespace.split(".")
        target_database = self.client[dbcol[0]]
        target_coll=target_database[dbcol[1]]

        for name,ix in collIndex.items():
            if ix.get("unique"):
                target_coll.create_index(ix["key"], name=name, unique=ix["unique"])
            else:
                target_coll.create_index(ix["key"], name=name)

        if dist_method_info:
            self.client.admin.command('enableSharding', dbcol[0])
            self.client.admin.command('shardCollection', namespace, key=dist_method_info["key"])

    def find_secondary(self):
        sec=list()
        for member in self.client.admin.command("replSetGetStatus")["members"]:
            if member["stateStr"]=="SECONDARY":
                sec.append(member["name"])
        return sec

    def find_primary(self):
        for member in self.client.admin.command("replSetGetStatus")["members"]:
            if member["stateStr"]=="PRIMARY": # the number of primary is one
                return member["name"]

    def collstats(self, namespace:str):
        dbcol = namespace.split(".")
        database = self.client[dbcol[0]]
        col = database[dbcol[1]]
        return list(col.aggregate([{"$collStats":{"storageStats":{}}}]))[0]["storageStats"]
        #return database.command("collstats", dbcol[1])

    def stepdown(self):
        self.client.admin.command("replSetStepDown", 60)

    def shutdown(self):
        try:
            self.client.admin.command("shutdown")
        except pymongo.errors.AutoReconnect:
            print("shutdown successfully")
