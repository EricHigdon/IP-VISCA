# https://pro.sony/s3/2019/01/16020225/AES6100121.pdf
# https://gitlab.viarezo.fr/2018corona/viscaoverip/blob/master/camera2.py
# sudo apt install python3-tk

import socket
import binascii # for printing the messages we send, not really necessary
from time import sleep
from tkinter import *
from tkinter import font
from multiprocessing import Process

# for receiving
buffer_size = 1024
#s.bind(('', camera_port)) # use the port one higher than the camera's port
#s.settimeout(1) # only wait for a response for 1 second


# Payloads
#received_message = '' # a place to store the OSC messages we'll receive
sequence_number = 1 # a global variable that we'll iterate each command, remember 0x0001
#reset_sequence_number = '02 00 00 01 00 00 00 01 01'

camera_on = '81 01 04 00 02 FF'
camera_off = '81 01 04 00 03 FF'

information_display_on = '81 01 7E 01 18 02 FF'
INFO_OFF = '81 01 7E 01 18 03 FF'

zoom_stop = '81 01 04 07 00 FF'
zoom_tele = '81 01 04 07 02 FF'
zoom_wide = '81 01 04 07 03 FF'
zoom_tele_variable = '81 01 04 07 2p FF' # p=0 (Low) to 7 (High)
zoom_wide_variable = '81 01 04 07 3p FF' # p=0 (Low) to 7 (High)
zoom_direct = '81 01 04 47 0p 0q 0r 0s FF' # pqrs: Zoom Position

memory_reset = '81 01 04 3F 00 0p FF'
SET_MEMORY = '81 01 04 3F 01 0{} FF' # p: Memory number (=0 to F)
SET_RECALL_SPEED = '81 01 06 01 {} FF'
RECALL = '81 01 04 3F 02 {} FF' # p: Memory number (=0 to F)

#Pan-tilt Drive
# VV: Pan speed setting 0x01 (low speed) to 0x18
# WW: Tilt speed setting 0x01 (low speed) to 0x17
movement_speed = '05'
pan_speed = movement_speed
tilt_speed = movement_speed
def set_speed(speed):
    global movement_speed
    global pan_speed
    global tilt_speed
    if len(speed) == 1:
        speed = '0{}'.format(speed)
    movement_speed = pan_speed = tilt_speed = speed
    return movement_speed

# YYYY: Pan Position DE00 to 2200 (CENTER 0000)
# ZZZZ: Tilt Position FC00 to 1200 (CENTER 0000)
#YYYY = '0000'
#ZZZZ = '0000'
def format_pan_tilt(value):
    print('moving at:', movement_speed)
    print('pan:', pan_speed, 'tilt:', tilt_speed)
    return value.format(pan_speed, tilt_speed)

def pan_up():
    return format_pan_tilt('81 01 06 01 {} {} 03 01 FF')
    
def pan_down():
    return format_pan_tilt('81 01 06 01 {} {} 03 02 FF')
    
def pan_left():
    return format_pan_tilt('81 01 06 01 {} {} 01 03 FF')
    
def pan_right():
    return format_pan_tilt('81 01 06 01 {} {} 02 03 FF')
    
def pan_up_left():
    return format_pan_tilt('81 01 06 01 {} {} 01 01 FF')
    
def pan_up_right():
    return format_pan_tilt('81 01 06 01 {} {} 02 01 FF')
    
def pan_down_left():
    return format_pan_tilt('81 01 06 01 {} {} 01 02 FF')
    
def pan_down_right():
    return format_pan_tilt('81 01 06 01 {} {} 02 02 FF')
    
def pan_stop():
    return format_pan_tilt('81 01 06 01 {} {} 03 03 FF')


JOYSTICK_BUTTONS = [
    {
        'text': '↖',
        'message': pan_up_left,
        'stop_message': pan_stop
    },
    {
        'text': '↑',
        'message': pan_up,
        'stop_message': pan_stop
    },
    {
        'text': '↗',
        'message': pan_up_right,
        'stop_message': pan_stop
    },
    {
        'text': '←',
        'message': pan_left,
        'stop_message': pan_stop
    },
    {
        'text': 'Stop',
        'message': pan_stop
    },
    {
        'text': '→',
        'message': pan_right,
        'stop_message': pan_stop
    },
    {
        'text': '↙',
        'message': pan_down_left,
        'stop_message': pan_stop
    },
    {
        'text': '↓',
        'message': pan_down,
        'stop_message': pan_stop
    },
    {
        'text': '↘',
        'message': pan_down_right,
        'stop_message': pan_stop
    }
]

ZOOM_BUTTONS = [
    {
        'text': 'Zoom In',
        'message': lambda: zoom_tele,
        'stop_message': lambda: zoom_stop
    },
    {
        'text': 'Zoom Stop',
        'message': lambda: zoom_stop
    },
    {
        'text': 'Zoom Out',
        'message': lambda: zoom_wide,
        'stop_message': lambda: zoom_stop
    }
]

FOCUS_BUTTONS = [
    {
        'text': 'Focus +',
        'message': lambda: focus_near,
        'stop_message': lambda: focus_stop
    },
    {
        'text': 'Focus Stop',
        'message': lambda: focus_stop
    },
    {
        'text': 'Focus -',
        'message': lambda: focus_far,
        'stop_message': lambda: focus_stop
    }
]

POWER_BUTTONS = [
    {
        'text': 'Camera On',
        'message': lambda: camera_on
    },
    {
        'text': 'Camera Off',
        'message': lambda: camera_off
    }
]

#pan_absolute_position = '81 01 06 02 VV WW 0Y 0Y 0Y 0Y 0Z 0Z 0Z 0Z FF'.replace('VV', str(VV)) #YYYY[0]
#pan_relative_position = '81 01 06 03 VV WW 0Y 0Y 0Y 0Y 0Z 0Z 0Z 0Z FF'.replace('VV', str(VV))
pan_home = '81 01 06 04 FF'
pan_reset = '81 01 06 05 FF'
zoom_direct = '81 01 04 47 0p 0q 0r 0s FF' # pqrs: Zoom Position
zoom_focus_direct = '81 01 04 47 0p 0q 0r 0s 0t 0u 0v 0w FF' # pqrs: Zoom Position  tuvw: Focus Position

inquiry_lens_control = '81 09 7E 7E 00 FF'
# response: 81 50 0p 0q 0r 0s 0H 0L 0t 0u 0v 0w 00 xx xx FF
inquiry_camera_control = '81 09 7E 7E 01 FF'

focus_stop = '81 01 04 08 00 FF'
focus_far = '81 01 04 08 02 FF'
focus_near = '81 01 04 08 03 FF'
focus_far_variable = '81 01 04 08 2p FF'.replace('p', '7') # 0 low to 7 high
focus_near_variable = '81 01 04 08 3p FF'.replace('p', '7') # 0 low to 7 high
focus_direct = '81 01 04 48 0p 0q 0r 0s FF' #.replace('p', ) q, r, s
focus_auto = '81 01 04 38 02 FF'
focus_manual = '81 01 04 38 03 FF'
focus_infinity = '81 01 04 18 02 FF'


class App:
    root = None
    ips = ['192.168.50.68:52381']
    ip = '192.168.50.68'
    port = '52381'
    rcvport = 0
    
    out_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # IPv4, UDP
    out_socket.settimeout(2)
    

    def __init__(self):
        # start by resetting the sequence number
        self.reset_sequence_number()
        #self.listener = Process(target=self.listen)
        #self.listener.start()
        self.run()

    def listen(self):
        while True:
            print('binding to port', self.rcvport, type(self.rcvport))
            self.out_socket.bind(('', self.rcvport))
            print('listening on port', self.rcvport)
            try:
                message, address = self.out_socket.recvfrom(1024)
                print('Received data from:', address, '\n', message)
            except socket.timeout:
                continue

    def close(self):
        #self.listener.terminate()
        #self.listener.join()
        self.root.destroy()

    def recall(self, memory_number):
        if len(str(memory_number)) == 1:
            memory_number = '0{}'.format(memory_number)
        message_string = RECALL.format(memory_number)
        self.send_message(INFO_OFF) # otherwise we see a message on the camera output
        sleep(0.25)
        message = self.send_message(message_string)
        sleep(1)
        self.send_message(INFO_OFF)
        return message

    def set_memory(self, memory_number):
        message_string = SET_MEMORY.format(memory_number)
        message = self.send_message(message_string)
        return message
       
    def set_camera(self, index):
        self.ip, self.port = self.ips[index].split(':')

    def set_speed(self, speed):
        self.speed = set_speed(speed)
        self.send_message(SET_RECALL_SPEED.format(self.speed))
        
    def add_cam_buttons(self):
        self.camera_buttons = []
        if len(self.ips) > 1:
            for i, ip in enumerate(self.ips):
                button = Button(
                    self.root,
                    text='Cam {}'.format(i+1),
                    command=lambda i=i: self.set_camera(i)
                    )
                button.grid(row=0, column=i)
                self.camera_buttons.append(button)
        else:
            self.set_camera(0)

    def add_preset_buttons(self):
        row = 2
        for i in range(12):
            col = i
            if col > 3 and col < 8:
                col = col - 4
            elif col > 7:
                col = col - 8
            if i > 3 and i < 8:
                row = 3
            elif i > 7:
                row = 4
            photo = PhotoImage(file='images/{}.png'.format(i)).subsample(3, 3)
            button_font = font.Font(size=24)
            Button(
                self.root,
                text=i,
                image=photo,
                compound=CENTER,
                width=464,
                height=261,
                fg='white',
                font=button_font,
                command=lambda i=i: self.recall(i)
            ).grid(row=row, column=col)
            setattr(self, 'photo_{}'.format(i), photo)

    def send_message(self, message_string):
        #global received_message
        payload_type = bytearray.fromhex('01 00')
        payload = bytearray.fromhex(message_string)
        payload_length = len(payload).to_bytes(2, 'big')
        message = payload_type + payload_length + self.sequence_number.to_bytes(4, 'big') + payload
        
        self.sequence_number += 1
        self.out_socket.sendto(message, (self.ip, int(self.port)))
        print('Sent Message', message)
        '''
        _, self.rcvport = self.out_socket.getsockname()
        print('set rcvport to', self.rcvport, type(self.rcvport))
        # TODO: add a timeout in case we don't hear back
        try:
            data = s.recvfrom(buffer_size)
            received_message = binascii.hexlify(data[0])
            print('Received', received_message)
            data = s.recvfrom(buffer_size)
            received_message = binascii.hexlify(data[0])
            print('Received', received_message)
        except socket.timeout: # s.settimeout(2.0) #above
            received_message = 'No response from camera'
            print(received_message)
        #if received_message == b'01110003000000119051ff':
        if received_message[0:4] == '0111':
            display_message.set('Connected')
        else:
            display_message.set(received_message[0:4])
        #'''
        received_message = 'test'
        return received_message

    def reset_sequence_number(self):
        reset_sequence_number_message = bytearray.fromhex('02 00 00 01 00 00 00 01 01')
        self.out_socket.sendto(reset_sequence_number_message,(self.ip, int(self.port)))
        self.sequence_number = 1
        return self.sequence_number

    def start_move(self, direction):
        self.send_message(direction)

    def add_buttons(self, buttons, start_col=0, start_row=0, max_col=2):
        row = start_row
        col = start_col
        for button_data in buttons:
            message = button_data['message']
            button = Button(
                self.joystick,
                text=button_data['text'],
                bg='black',
                fg='white',
            )
            button.grid(row=row, column=col)
            button.bind(
                '<ButtonPress-1>',
                lambda event, message=message: self.send_message(message())
            )
            if 'stop_message' in button_data:
                message = button_data['stop_message']
                button.bind(
                    '<ButtonRelease-1>',
                    lambda event, message=message: self.send_message(message())
                )
            if col == max_col:
                col = 0
                row += 1
            else:
                col += 1


    def run(self):
        # GUI
        if self.root is None:
            self.root = Tk()
            self.root.columnconfigure(0, weight=1, minsize=75)
            self.root.columnconfigure(1, weight=1, minsize=75)
            self.root.columnconfigure(2, weight=1, minsize=75)
            self.root.columnconfigure(3, weight=1, minsize=75)
            self.root.rowconfigure(2, weight=1, minsize=50)
            self.root.rowconfigure(3, weight=1, minsize=50)
            self.root.rowconfigure(4, weight=1, minsize=50)

            self.root.configure(bg='black')

            display_message = StringVar()
            self.root.title('VISCA IP Camera Controller')
            #Label(self.root, text='VISCA IP Camera Controller').grid(row=0, column=0, columnspan=100)
            self.add_cam_buttons()
            #Button(self.root, text='Connect', command=self.reset_sequence_number()).grid(row=1, column=6)
            
            #Label(self.root, text='Presets').grid(row=1, column=0, columnspan=2)
            self.add_preset_buttons()

            self.joystick = Frame(self.root, bg='black')

            self.add_buttons(JOYSTICK_BUTTONS)
            self.add_buttons(ZOOM_BUTTONS, start_col=3, max_col=5)
            self.add_buttons(FOCUS_BUTTONS, start_col=3, start_row=1, max_col=5)
            self.add_buttons(POWER_BUTTONS, start_col=3, start_row=2, max_col=5)

            Button(self.joystick,
                text='Home',
                bg='black',
                fg='white',
                command=lambda: self.send_message(pan_home)
            ).grid(row=3, column=1)

            ## slider to set speed for pan_speed and tilt_speed (0x01 to 0x17)
            ## still not quite sure about this...
            scale = Scale(self.joystick,
                from_=1,
                to=17,
                bg='black',
                fg='white',
                bd=0,
                command=self.set_speed, orient=HORIZONTAL, label='Speed'
            )
            scale.grid(row=4, column=0, columnspan=3)
            scale.set(movement_speed)

            self.joystick.grid(row=5, column=3)

        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.mainloop()

if __name__ == '__main__':
    app = App()
