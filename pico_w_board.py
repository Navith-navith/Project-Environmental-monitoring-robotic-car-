import _thread
import network
import socket
from time import sleep
import machine
from machine import Pin, PWM
import time
import utime,time
from machine import Pin, I2C
from sh1106 import SH1106_I2C
import urequests as requests
from easy_comms import Easy_comms
import dht

com1 = Easy_comms(uart_id=0, baud_rate=9600)
#com1.start()
ssid = 'YourSSID'
password = 'YourPASSWORD'
vcc_dht=Pin(21,Pin.OUT)
vcc_dht.high()

def read_dht():
    dht_sensor = dht.DHT11(machine.Pin(16))
    time.sleep(1)
    dht_sensor.measure()
    temperature = dht_sensor.temperature()
    humidity = dht_sensor.humidity()
    return [temperature,humidity]

speed = 30000
Mot_A_Forward = Pin(7, Pin.OUT)
Mot_A_Back = Pin(9, Pin.OUT)
EN_A = PWM(Pin(6))

Mot_B_Forward = Pin(10, Pin.OUT)
Mot_B_Back = Pin(11, Pin.OUT)
EN_B = PWM(Pin(12))

trigger = Pin(14, Pin.OUT)
echo = Pin(15, Pin.IN)
led = Pin(8, Pin.OUT)

EN_A.freq(1000)
EN_B.freq(1000)

def oled_data(Data):
    for i, j in Data.items():
        WIDTH = 128
        HEIGHT = 64
        i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=600961)
        oled = SH1106_I2C(WIDTH, HEIGHT, i2c)
        oled.fill(0)
        oled.text(i, 5, 35)
        oled.text(str(j), 5, 45)
        oled.show()
        time.sleep(1.5)
    oled.fill(0)
    i="DATA COLLECTED"
    oled.text(i, 5, 15)
    oled.show()

def data_process():
    try:
        com1.send("Data_Request")
        sleep(5)
        timeout=time.time()+10
        while True:
            message=""
            message = com1.read()
            if time.time() > timeout:
                print("timeout")
                break
            if message is not None:
                print(f"Message received: {message.strip('\n')}")      
                Data = {}
                for pair in message.split(','):
                    key, value = pair.split(':')
                    Data[key]=value
                dht_data=read_dht()
                Data["dht_temp_data"] = dht_data[0]
                Data["dht_humidity_data"] = dht_data[1]
                oled_data(Data)
                
                
                server_url = 'http://192.168.31.132:5000/upload'
                response = requests.post(server_url, json=Data,timeout=10)#, headers={'Content-Type': 'application/json'})
                response.close()
                break
            

    except Exception as e:
        print("An error occurred:", e)
 
servo_pin = 20
servo = PWM(Pin(servo_pin))
servo.freq(50)
servo.duty_ns(0)

def rotate_motor(angle):
    duty_cycle = int(500 + angle * 2000 / 180)  # Convert angle to duty cycle
    servo.duty_ns(duty_cycle * 1000)  # Set duty cycle in nanoseconds
    time.sleep(0.5)  # Wait for servo to reach the desired position
    servo.duty_ns(0)  # Turn off the servo

# Stop the robot as soon as possible
def move_stop():
    EN_A.duty_u16(0)
    Mot_A_Forward.low()
    Mot_A_Back.low()

    EN_B.duty_u16(0)
    Mot_B_Forward.low()
    Mot_B_Back.low()

def move_forward():
    EN_A.duty_u16(speed)
    Mot_A_Back.low()
    Mot_A_Forward.high()

    EN_B.duty_u16(speed)
    Mot_B_Back.low()
    Mot_B_Forward.high()

def move_left():
    EN_A.duty_u16(25000)
    Mot_A_Forward.low()
    Mot_A_Back.high()

    EN_B.duty_u16(25000)
    Mot_B_Back.low()
    Mot_B_Forward.high()

def move_backward():
    EN_A.duty_u16(speed)
    Mot_A_Forward.low()
    Mot_A_Back.high()

    EN_B.duty_u16(speed)
    Mot_B_Forward.low()
    Mot_B_Back.high()

def move_right():
    EN_A.duty_u16(25000)
    Mot_A_Forward.high()
    Mot_A_Back.low()

    EN_B.duty_u16(25000)
    Mot_B_Back.high()
    Mot_B_Forward.low()

def measure_distance(echo_pin,trigger):
    import utime
    while True:
        trigger.low()
        utime.sleep_us(2)
        trigger.high()
        utime.sleep_us(5)
        trigger.low()
        while echo_pin.value() == 0:
            signaloff = utime.ticks_us()
        while echo_pin.value() == 1:
            signalon = utime.ticks_us()
        timepassed = signalon - signaloff
        dist = (timepassed * 0.0343) / 2
        utime.sleep(0.01)
        if dist < 30:
            print("Distance less")
            move_stop()
            move_backward()
            print(dist)
            utime.sleep(0.1)
            move_stop()
            led.high()
            utime.sleep(0.01)
            led.low()
            

def connect():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    while not wlan.isconnected():
        print('Waiting for connection...')
        sleep(1)
    ip = wlan.ifconfig()[0]
    print(f'Connected on {ip}')
    return ip

def open_socket(ip):
    address = (ip, 80)
    connection = socket.socket()
    connection.bind(address)
    connection.listen(1)
    return connection

def serve(connection):
    while True:
        rotate_motor(90)
        client = connection.accept()[0]
        request = client.recv(1024)
        request = str(request)
        try:
            request = request.split()[1]
        except IndexError:
            pass
        if request == '/forward?':
            move_forward()
        elif request == '/left?':
            rotate_motor(180)
            move_left()
            rotate_motor(90)
        elif request == '/stop?':
            move_stop()
        elif request == '/right?':
            rotate_motor(0)
            move_right()
            rotate_motor(90)
        elif request == '/back?':
            move_backward()
        elif request =='/upload_data?':
            move_stop()
            data_process()
        html = webpage()
        client.send(html)
        client.close()

def webpage():
    html = """
            <!DOCTYPE html>
            <html>
            <head>
            <title>EEX Robot Control</title>
            <style>
            /* Add CSS styles for buttons */
            .button {
                height: 120px;
                width: 120px;
                background-color: #4CAF50; /* Green background */
                border: none;
                color: white;
                padding: 20px;
                text-align: center;
                text-decoration: none;
                display: inline-block;
                font-size: 16px;
                margin: 4px 2px;
                cursor: pointer;
                box-shadow: 0 6px #999;
                border-radius: 10px; /* Curved edges */
            }

            .button:hover {
                background-color: #45a049; /* Darker green background on hover */
                box-shadow: 0 12px #999;
            }

            .button:active {
                background-color: #3e8e41; /* Active state background color */
                box-shadow: 0 3px #666;
            }

            /* Style for the "Get and Upload Data" button */
            #get-upload-button {
                background-color: #008CBA; /* Light blue background */
                width: 360px; /* Adjusted width */
                border-radius: 20px; /* Slightly curved edges */
            }

            /* Style for the "Stop" button */
            .stop-button {
                background-color: #FF0000; /* Red background */
                box-shadow: 0 4px #999; /* Reduced shadow length */
            }

            /* Override hover style for stop button */
            .stop-button:hover {
                background-color: #FF0000; /* Red background on hover */
            }
            </style>
            </head>
            <center><b>
            <form action="./forward">
            <input type="submit" value="Forward" class="button" />
            </form>
            <table><tr>
            <td><form action="./left">
            <input type="submit" value="Left" class="button" />
            </form></td>
            <td><form action="./stop">
            <input type="submit" value="Stop" class="button stop-button" />
            </form></td>
            <td><form action="./right">
            <input type="submit" value="Right" class="button" />
            </form></td>
            </tr></table>
            <form action="./back">
            <input type="submit" value="Back" class="button" />
            </form>
            <form action="./upload_data">
            <input type="submit" value="Get and Upload Data" id="get-upload-button" class="button" />
            </form>
            </body>
            </html>
            """
    return html
def start_measurement_thread(echo,trigger):
    _thread.start_new_thread(measure_distance, (echo,trigger,))
try:
    start_measurement_thread(echo,trigger)
    ip = connect()
    WIDTH = 128
    HEIGHT = 64
    i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=600961)
    oled = SH1106_I2C(WIDTH, HEIGHT, i2c)
    oled.fill(0)
    oled.text(str(ip), 5, 25)
    oled.show()
    connection = open_socket(ip)
    serve(connection)
except KeyboardInterrupt:
    WIDTH = 128
    HEIGHT = 64
    i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=600961)
    oled = SH1106_I2C(WIDTH, HEIGHT, i2c)
    oled.fill(0)
    oled.show()
    
    machine.reset()
