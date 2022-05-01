import subprocess
from subprocess import CREATE_NO_WINDOW
import orjson
from time import sleep
from threading import Thread
from queue import Queue, Empty
import os
import sys
import re
from time import sleep
import requests

log = []

# get subprocess output without blocking


def enqueue_output(out, queue):
    for line in iter(out.readline, b''):
        queue.put(line)
    out.close()

# -FUNCTION ADAPTER-


def startAdapter(Proxy):
    # function takes URI and creates the adapter using a non-blocking subprocess
    # function returns the adapterprocess, interfaceList, and error code
    # create wintun adapter and use shadowsocks proxy profile
    print("Creating Adapter...")
    adapterProcess = subprocess.Popen(get_path(
        "dep\\tun2socks-windows-amd64.exe ") + f"--device tun://wintun -proxy {Proxy} --loglevel debug", creationflags=CREATE_NO_WINDOW, stdout=subprocess.PIPE)

    # https://stackoverflow.com/a/4896288
    q = Queue()
    t = Thread(target=enqueue_output, args=(adapterProcess.stdout, q))
    t.daemon = True  # thread dies with the program
    t.start()

    # check if adapter started
    interfaceList, error = getAdapterID(q)  # Get adapter ID

    return adapterProcess, interfaceList, error

# -FUNCTION CONNECT-


def redirectTraffic(IP, interfaceList):
    # function routes the traffic into the created adapter
    # function takes the IP and interfaceList
    # function returns boolean if successful or string containing error

    # set ip address
    subprocess.call('netsh interface ip set address name="wintun" source=static addr=192.168.123.1 mask=255.255.255.0 gateway=none',
                    creationflags=CREATE_NO_WINDOW)
    # route traffic to wintun adapter
    subprocess.call(
        f"route add 0.0.0.0 mask 0.0.0.0 192.168.123.1 if {interfaceList} metric 5", creationflags=CREATE_NO_WINDOW)

    # Get defaultGetway
    defaultGateway = subprocess.check_output(
        "ipconfig | findstr Default | findstr /n 0", shell=True)
    defaultGateway = defaultGateway.decode("utf-8")
    # get first default gateway
    defaultGateway = re.findall(r'[0-9]+(?:\.[0-9]+){3}', defaultGateway)[0]

    subprocess.call(
        f"route add {IP} mask 255.255.255.255 {defaultGateway}", creationflags=CREATE_NO_WINDOW)

    # keep checking my ip for connectivity
    return checkConnectivity(IP)


def getAdapterID(q):
    # Get interface adapter interface id
    # function takes the queue to append errors
    # function returns the interfacelist and error code
    print("Getting Adapter id...")
    # keep trying for 5 seconds
    for i in range(0, 5):
        while(True):
            try:
                interfaceList = subprocess.check_output(
                    'route print | findstr WireGuard', shell=True)
                interfaceList = interfaceList.decode("utf-8")
                interfaceList = interfaceList[1:3]
                return interfaceList, 0
            except BaseException as e:
                print('Failed to find interface ' + str(e))
                log.append(str(e))
                sleep(1)
                # if problem identified, exit to notify user
                try:
                    line = q.get_nowait()
                    log.append(str(line))
                    print("log: ", log)
                    if "Access is denied" in str(line):
                        return 0, 1  # exit to notify user
                except Empty:
                    print('no output yet')

            break
    return line, 1


def checkConnectivity(IP):
    # Check if IP address matches the VPS IP
    # function takes IP address
    # function returns boolean if successful or string containing error
    try:
        # Get public IP
        ip = requests.get('https://api.ipify.org/', timeout=10).content.decode('utf8')
        if ip == str(IP):  # Check if my IP matches the VPS IP
            print('VPN Connected')
            return True
    except BaseException as e:
        if "11004" in str(e) or "11001" in str(e):      #there may be other error codes on other systems
            print("Establishing Connection...")
            sleep(1)
            return checkConnectivity(IP)
        elif "10054" in str(e):
            return "VPN Connection Failed: Timeout" + str(e)
        else:
            print(str(e))
            return "VPN Connection timed out" + str(e)

# save user's input


def saveInput(values):
    # function saves the user input in a json file
    with open("input.json", "wb") as file:
        file.write(orjson.dumps(values))


def get_path(filename):
    # adjust path for executable
    # function takes the file path
    # function returns the path after adjusting it for executing
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, filename)
    else:
        return filename
