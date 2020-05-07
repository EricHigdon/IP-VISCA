# https://pro.sony/s3/2019/01/16020225/AES6100121.pdf
# https://gitlab.viarezo.fr/2018corona/viscaoverip/blob/master/camera2.py
# sudo apt install python3-tk

import socket
import binascii # for printing the messages we send, not really necessary
from time import sleep
from tkinter import *
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
RECALL = '81 01 04 3F 02 0{} FF' # p: Memory number (=0 to F)

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
    ips = ['127.0.0.1:52381']
    ip = '127.0.0.1'
    port = '52381'
    
    out_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # IPv4, UDP
    in_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # IPv4, UDP
    in_socket.bind(('', int(port)))

    def __init__(self):
        # start by resetting the sequence number
        self.reset_sequence_number()
        self.listener = Process(target=self.listen)
        self.listener.start()
        self.run()

    def listen(self):
        while True:
            message, address = self.in_socket.recvfrom(1024)
            print('Received data from:', address, '\n', message)

    def close(self):
        self.listener.terminate()
        self.listener.join()
        self.root.destroy()

    def recall(self, memory_number):
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
            
    def send_message(self, message_string):
        #global received_message
        payload_type = bytearray.fromhex('01 00')
        payload = bytearray.fromhex(message_string)
        payload_length = len(payload).to_bytes(2, 'big')
        message = payload_type + payload_length + self.sequence_number.to_bytes(4, 'big') + payload
        
        self.sequence_number += 1
        self.out_socket.sendto(message, (self.ip, int(self.port)))
        print('Sent Message', message)
        # TODO: add a timeout in case we don't hear back
        '''
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

    def run(self):
        # GUI
        if self.root is None:
            self.root = Tk()
            display_message = StringVar()
            self.root.title('VISCA IP Camera Controller')
            #Label(self.root, text='VISCA IP Camera Controller').grid(row=0, column=0, columnspan=100)
            self.add_cam_buttons()
            Button(self.root, text='Connect', command=self.reset_sequence_number()).grid(row=1, column=6)
            Button(self.root, text='Cam On', command=lambda: self.send_message(camera_on)).grid(row=2, column=6)
            Button(self.root, text='Cam Off', command=lambda: self.send_message(camera_off)).grid(row=3, column=6)

            Label(self.root, text='Presets').grid(row=1, column=0, columnspan=2)
            Button(self.root, text=0, command=lambda: self.recall(0)).grid(row=2, column=0)
            Button(self.root, text=1, command=lambda: self.recall(1)).grid(row=2, column=1, padx=5)
            Button(self.root, text=2, command=lambda: self.recall(2)).grid(row=3, column=0)
            Button(self.root, text=3, command=lambda: self.recall(3)).grid(row=3, column=1)
            Button(self.root, text=4, command=lambda: self.recall(4)).grid(row=4, column=0)
            Button(self.root, text=5, command=lambda: self.recall(5)).grid(row=4, column=1)

            Button(self.root, text='↑', command=lambda: self.send_message(pan_up())).grid(row=1, column=3)
            Button(self.root, text='←', command=lambda: self.send_message(pan_left())).grid(row=2, column=2)
            Button(self.root, text='→', command=lambda: self.send_message(pan_right())).grid(row=2, column=4)
            Button(self.root, text='↓', command=lambda: self.send_message(pan_down())).grid(row=3, column=3)
            Button(self.root, text='↖', command=lambda: self.send_message(pan_up_left())).grid(row=1, column=2)
            Button(self.root, text='↗', command=lambda: self.send_message(pan_up_right())).grid(row=1, column=4)
            Button(self.root, text='↙', command=lambda: self.send_message(pan_down_left())).grid(row=3, column=2)
            Button(self.root, text='↘', command=lambda: self.send_message(pan_down_right())).grid(row=3, column=4)
            Button(self.root, text='Stop', command=lambda: self.send_message(pan_stop())).grid(row=2, column=3)
            Button(self.root, text='Home', command=lambda: self.send_message(pan_home)).grid(row=4, column=3)

            # slider to set speed for pan_speed and tilt_speed (0x01 to 0x17)
            # still not quite sure about this...
            scale = Scale(self.root, from_=1, to=17, command=self.set_speed, orient=HORIZONTAL, label='Speed')
            scale.grid(row=5, column=2, columnspan=3)
            scale.set(movement_speed)

            Button(self.root, text='Zoom In', command=lambda: self.send_message(zoom_tele)).grid(row=1, column=5)
            Button(self.root, text='Zoom Stop', command=lambda: self.send_message(zoom_stop)).grid(row=2, column=5)
            Button(self.root, text='Zoom Out', command=lambda: self.send_message(zoom_wide)).grid(row=3, column=5)

            Button(self.root, text='Focus Near', command=lambda: self.send_message(focus_near)).grid(row=4, column=5)
            Button(self.root, text='Focus Far', command=lambda: self.send_message(focus_far)).grid(row=5, column=5)

            Button(self.root, text='Info Off', command=lambda: self.send_message(INFO_OFF)).grid(row=5, column=6)

            # Connection Label
            Label(self.root, textvariable=display_message).grid(row=6, column=4, columnspan=3)

        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.mainloop()

app = App()