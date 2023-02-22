import paramiko

DEBUG_MODE = False

class ServerCommand:
    def __init__(self, host):
        self.host = host
        self.user = "root"
        self.debug = DEBUG_MODE

    def _executor(self, command):
        try:
            if self.debug:
                print(self.host, command)
            ssh=paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname = self.host, username = self.user)
            try:
                stdin, stdout, stderr = ssh.exec_command(command)
            except Exception as e:
                print(f"connection is failed {e}")

            rtnValue = stdout.channel.recv_exit_status()
            retOut = stdout.read().decode('utf-8')
            retErr = stderr.read().decode('utf-8')

            if self.debug:
                print(rtnValue, retOut, retErr)

            if self.debug and rtnValue == 0:
                print(f"command is successfully executed, {command} ")
        except Exception as e:
            print(f"exception occur {e}")
        finally:
            ssh.close()

    def dependency(self):
        self._executor("yum install snappy-devel libzstd-devel zlib-devel -y")

    def rsync(self, hostname, mongo_path, db, mypath, mydb):
        self._executor(f"rsync --bwlimit=150M -av --no-perms -e \"ssh -o StrictHostKeyChecking=no\" root@{hostname}:{mongo_path}/{db} {mypath}/{mydb}")

    def salvage(self, dbpath, colpath):
        self._executor(f"/tmp/wt -v -h {dbpath} -R salvage {colpath}")

    def start(self, command: str): #TODO
        if command:
            self._executor(command)
        else:
            self._executor("systemctl restart mongod")
