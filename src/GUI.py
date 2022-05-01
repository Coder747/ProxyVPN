from lib2to3.pytree import Base
import PySimpleGUI as sg
import re
import orjson
import VPN
import ctypes
import platform

# make UI work well with different resolutions


def make_dpi_aware():
    if int(platform.release()) >= 8:
        ctypes.windll.shcore.SetProcessDpiAwareness(True)


make_dpi_aware()

sg.theme('DarkAmber')   # Add a little color to your windows

Title = sg.Text('ProxyVPN', size=(0, 2),
                font='Courier 25 bold', key='title')

ProxyInput = sg.Input(pad=(10, 15), key="Proxy")

Button = sg.Button('Connect', pad=(0, 25), key='button',
                   font='Courier 12 bold', size=(14, 2))

Status = sg.Text('Disconnected', font='Courier 20 bold',
                 text_color="#ed4245", key='status')

Loading = sg.Image(VPN.get_path('images\invisible.png'), key='-gif-')


layout = [
    [sg.VPush()],
    [sg.Push(), Title, sg.Push()],
    [sg.Text('Proxy'), sg.Push(), ProxyInput],
    [sg.Push(), Button, sg.Push()],
    [sg.Push(), Status, sg.Push()],
    [sg.Push(), Loading, sg.Push()],
    [sg.VPush()]
]

window = sg.Window('ProxyVPN', layout)


loading, connected, adapterProcess, saved = 0, 0, 0, 0
while True:  # Event Loop
    # make read non-breaking so we can update the gif every 50ms
    event, values = window.read(100)
    # retrieve user's input
    if saved != 1:
        try:
            with open('input.json', "rb") as file:
                values = orjson.loads(file.read())
                window['Proxy'].Update(values.get('Proxy').strip())
                saved = 1

        except BaseException as e:
            print('No saved input', e)
            saved = 1

    # closing app
    if event == sg.WIN_CLOSED or event == 'Exit':
        if adapterProcess != 0:
            adapterProcess.terminate()  # kill subprocess
            adapterProcess.wait()
        break
    elif event == 'button':
        # if vpn is disconnected then connect and  vice versa
        if connected == 0:  # if vpn is disconnected
            print("Starting adapter...")
            window['button'].Update(text='Initiating...')
            window['button'].update(disabled=True)
            loading = 1
            window.perform_long_operation(
                lambda: VPN.saveInput(values), '-FUNCTION SAVED-')  # start the adapter
            window.perform_long_operation(
                lambda: VPN.startAdapter(values.get('Proxy').strip()), '-FUNCTION ADAPTER-')  # start the adapter
        else:  # if vpn is connected
            adapterProcess.terminate()
            adapterProcess.wait()
            connected = 0
            window['button'].Update(text='Connect')
            window['status'].Update('Disconnected')
            window['status'].Update(text_color="#ed4245")

    elif event == '-FUNCTION ADAPTER-':
        adapterProcess, interfaceList, error = values.get('-FUNCTION ADAPTER-')
        if error != 0:
            sg.popup_error("Failed to create adapter interface. Please run the program as administartor.",
                           grab_anywhere=True, title="Permission Error")
            connected, loading = 0, 0
            window['button'].update(disabled=False)
            window['button'].Update(text='Connect')
            continue

        print("Redirecting traffic...")
        # Redirect traffic to adapter

        try:
            IP = re.findall(r'[0-9]+(?:\.[0-9]+){3}', values.get('Proxy'))[0]
        except BaseException as e:
            adapterProcess.terminate()
            adapterProcess.wait()
            sg.popup_error("Incorrect input format.",
                           grab_anywhere=True, title="Incorrect input")
            loading = 0
            window['button'].update(disabled=False)
            window['button'].update('Connect')
            continue

        window.perform_long_operation(lambda: VPN.redirectTraffic(
            IP, interfaceList), '-FUNCTION CONNECT-')  # get IP from user then redirect traffic
        window['button'].Update(text='Connecting...')

    elif event == '-FUNCTION CONNECT-':  # if vpn connects successfully
        if values.get('-FUNCTION CONNECT-') == True:
            connected, loading = 1, 0
            window['button'].Update(text='Disconnect')
            window['status'].Update('Connected')
            window['status'].Update(text_color="#a8ff60")
            window['button'].update(disabled=False)
        else:  # if vpn fails to connect
            adapterProcess.terminate()
            adapterProcess.wait()
            connected, loading = 0, 0
            window['button'].Update(text='Connect')
            window['button'].update(disabled=False)
            sg.popup_error(values.get('-FUNCTION CONNECT-'),
                           grab_anywhere=True, title="Connection Error")

    elif loading == 0:
        window['-gif-'].Update(filename=VPN.get_path("images\invisible.png"))
        continue
    # Update gif every 50ms
    window['-gif-'].UpdateAnimation(VPN.get_path("images\loading.gif"),
                                    time_between_frames=100)


window.close()
