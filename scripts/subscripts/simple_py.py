import sys
import json

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Error! Usage: python3 subscripts/simple_py.py string')
    info = json.loads(sys.argv[1])
    #print(info)

    for i in info:
        print(i['id'])