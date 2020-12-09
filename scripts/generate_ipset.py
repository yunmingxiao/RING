import json
import os
import subprocess
# import Constants

def bytes2str(s):
    if type(s) is bytes:
        return s.decode('utf8')
    else:
        print('This is %s not bytes. Convesion Error!' % str(type(s)))
        return ''

name_dict = {
    "PUPs": "PUPs (potentially unwanted programs)",
    "Medium": "Medium Risk",
    "High": "High Risk",
    "Spyware": "Spyware/Adware/Keyloggers",
    "P2P Sharing": "P2P/File Sharing",
}
def name_translate(name):
    if name in name_dict:
        return name_dict[name]
    else:
        return name

class IPSet():
    def __init__(self, path):
        self.path = path

    def create_all(self, names):
        for name in names:
            dsts = set([])
            nn = name_translate(name)
            for dst in self.security:
                if nn in self.security[dst]:
                    dsts.add(dst)
            for dst in self.category:
                if nn in self.category[dst]:
                    dsts.add(dst)

            maxelem = 65536
            while (maxelem < len(dsts)): maxelem *= 2
            print(len(dsts), maxelem)

            set_name = name.replace(' ', '-')
            self.destroy_ipset(set_name)
            self.create_ipset(set_name, maxelem)
            for dst in dsts:
                self.block(set_name, dst)
            self.save_ipset(set_name, "%s/%s.ipset" % (self.path, set_name))
            

    def create_ipset(self, set_name, max_len=65536):
        cmds = ['ipset', 'create', set_name, 'hash:net', 'maxelem', str(max_len)]
        print(cmds)
        p = subprocess.Popen(cmds, stdout=subprocess.PIPE)
        ans = bytes2str(p.communicate()[0])
        p.kill()
        if ans:
            print('IPSet.create_ipset failed!', ans)

    def destroy_ipset(self, set_name):
        cmds = ['ipset', 'destroy', set_name]
        print(cmds)
        p = subprocess.Popen(cmds, stdout=subprocess.PIPE)
        ans = bytes2str(p.communicate()[0])
        p.kill()
        if ans:
            print('IPSet.destroy_ipset failed!', ans)

    def check_ipset(self, set_name):
        cmds = ['ipset', 'list', set_name]
        print(cmds)
        p = subprocess.Popen(cmds, stdout=subprocess.PIPE)
        ans = bytes2str(p.communicate()[0])
        p.kill()
        if set_name not in ans:
            return False
            # self.create_ipset(set_name)
        else:
            return True

    def block(self, set_name, dst):
        cmds = ['ipset', 'add', set_name, "[%s]" % (dst)]
        print(cmds)
        p = subprocess.Popen(cmds, stdout=subprocess.PIPE)
        ans = bytes2str(p.communicate()[0])
        p.kill()
        # if dst_ip:
        #     cmds = ['iptables', '-I', 'FORWARD', '-s', dst_ip, '-j', 'DROP']
        # elif dst_url:
        #     cmds = ['iptables', '-I', 'FORWARD', '-d', dst_ip, '-j', 'DROP']

    def test(self, set_name, dst):
        cmds = ['ipset', 'test', set_name, "[%s]" % (dst)]
        print(cmds)
        p = subprocess.Popen(cmds, stdout=subprocess.PIPE)
        ans = bytes2str(p.communicate()[0])
        p.kill()
        return 'NOT' not in ans 

    def allow(self, set_name, dst):
        if self.test(dst):
            cmds = ['ipset', 'del', set_name, "[%s]" % (dst)]
            print(cmds)
            p = subprocess.Popen(cmds, stdout=subprocess.PIPE)
            ans = bytes2str(p.communicate()[0])
            p.kill()
            if ans:
                print('IPSet.allow failed!', ans)
    
    def get_rules(self, set_name):
        cmds = ['ipset', 'list', set_name]
        print(cmds)
        p = subprocess.Popen(cmds, stdout=subprocess.PIPE)
        ans = bytes2str(p.communicate()[0])
        p.kill()
        ans = ans.split('\n')
        if len(ans) < 8:
            print('IPSet.get_rules failed!', ans)
        self.rules = ans[8:]
        return self.rules

    def save_ipset(self, set_name, filename):
        cmds = ['ipset', 'save', set_name, '-f', filename]
        print(cmds)
        p = subprocess.Popen(cmds, stdout=subprocess.PIPE)
        ans = bytes2str(p.communicate()[0])
        p.kill()
        if ans:
            print('IPSet.save failed!', ans)

    def restore(self, filename):
        cmds = ['ipset', 'restore', '-f', filename]
        print(cmds)
        p = subprocess.Popen(cmds, stdout=subprocess.PIPE)
        ans = bytes2str(p.communicate()[0])
        p.kill()
        if ans:
            print('IPSet.restore failed!', ans)


if __name__ == "__main__":
    #ipset = IPSet("%s/filters" % (Constants.TARGET_DIR))
    ipset = IPSet(os.getcwd())
    ipset.create_all(['Medium', 'High', 'Unverified', 'Pornography', 
     'Potential Criminal Activities', 'Potential Illegal Software', 'Illegal UK', 
     'Malicious Downloads', 'Malicious Sites', 'Phishing', 'PUPs', 'Spam URLs', 
     'Browser Exploits', 'P2P Sharing', 'Spyware'])
