from bidict import bidict
import json

translation = bidict({
    "edk": "block-p2p-eDonkey/eMule/Overnet", 
    "dc": "block-p2p-Direct Connect", 
    "kazaa": "block-p2p-KaZaA", 
    "gnu": "block-p2p-Gnutella", 
    "bit": "block-p2p-BitTorrent", 
    "apple": "block-p2p-AppleJuice", 
    "winmx": "block-p2p-WinMX", 
    "soul": "block-p2p-SoulSeek", 
    "ares": "block-p2p-Ares", 
    "Medium": "block-risk-Medium", 
    "High": "block-risk-High", 
    "Unverified": "block-risk-Unverified", 
    "Pornography": "block-content-Pornography", 
    "Potential-Criminal-Activities": "block-content-Potential Criminal Activities", 
    "Potential-Illegal-Software": "block-content-Potential Illegal Software", 
    "Illegal-UK": "block-content-Illegal UK", 
    "Malicious-Downloads": "block-content-Malicious Downloads", 
    "Malicious-Sites": "block-content-Malicious Sites", 
    "Phishing": "block-content-Phishing", 
    "PUPs": "block-content-PUPs", 
    "Spam-URLs": "block-content-Spam URLs", 
    "Browser-Exploits": "block-content-Browser Exploits", 
    "P2P-Sharing": "block-content-P2P/File Sharing", 
    "Spyware": "block-content-Spyware/Adware/Keyloggers",
})
def translate(key):
    if key in translation:
        return translation[key]
    else:
        try:
            return translation.inverse[key]
        except:
            return key

def controller2web(config):
    if type(config) == str:
        config = json.loads(config)
    ret = {
        "block-p2p": {translate(key): config['p2p'][key] for key in config['p2p']}, 
        "block-risk": {},
        "block-content": {},
    }
    for key in config['ipset']:
        if key in ['Medium', 'High', 'Unverified']:
            ret['block-risk'][translate(key)] = config['ipset'][key]
        else:
            ret['block-content'][translate(key)] = config['ipset'][key]
    return ret

def web2controller(config):
    if type(config) == str:
        config = json.loads(config)
    ret = {
        "p2p": {translate(key): config['block-p2p'][key] for key in config['block-p2p']}, 
        "ipset": {},
    }
    for key in config['block-risk']:
        ret['ipset'][translate(key)] = config['block-risk'][key]
    for key in config['block-content']:
        ret['ipset'][translate(key)] = config['block-content'][key]
    return ret

a = json.dumps({
    "p2p": {
        "edk": True, 
        "dc": True, 
        "kazaa": True, 
        "gnu": True, 
        "bit": True, 
        "apple": True, 
        "winmx": False, 
        "soul": True, 
        "ares": True, 
    }, 
    "ipset": {
        "Medium": True, 
        "High": True, 
        "Unverified": True, 
        "Pornography": True, 
        "Potential Criminal Activities": True, 
        "Potential Illegal Software": True, 
        "Illegal UK": True, 
        "Malicious Downloads": True, 
        "Malicious Sites": True, 
        "Phishing": True, 
        "PUPs": True, 
        "Spam URLs": True, 
        "Browser Exploits": True, 
        "P2P/File Sharing": True, 
        "Spyware/Adware/Keyloggers": True,
    }
})
print(controller2web(a))

b = json.dumps({
    "block-p2p": {
        "block-p2p-edk": True, 
        "block-p2p-dc": True, 
        "block-p2p-kazaa": True, 
        "block-p2p-gnu": True, 
        "block-p2p-bit": True, 
        "block-p2p-apple": True, 
        "block-p2p-winmx": False, 
        "block-p2p-soul": True, 
        "block-p2p-ares": True, 
    }, "block-risk": {
        "block-risk-Medium": True, 
        "block-risk-High": True, 
        "block-risk-Unverified": True, 
    }, "block-content": {
        "block-content-Pornography": True, 
        "block-content-Potential Criminal Activities": True, 
        "block-content-Potential Illegal Software": True, 
        "block-content-Illegal UK": True, 
        "block-content-Malicious Downloads": True, 
        "block-content-Malicious Sites": True, 
        "block-content-Phishing": True, 
        "block-content-PUPs": True, 
        "block-content-Spam URLs": True, 
        "block-content-Browser Exploits": True, 
        "block-content-P2P/File Sharing": True, 
        "block-content-Spyware/Adware/Keyloggers": True,
    }
})

print(web2controller(b))

print(web2controller(controller2web(a)) == a)