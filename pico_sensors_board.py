from machine import Pin, ADC,UART
import math
from time import sleep
import utime
import machine
import time
from easy_comms import Easy_comms
from time import sleep
import _thread
############### NOISE SENSOR CONFIG ####################
noise_sensor = ADC(Pin(27))
sensor_min = 0        # Minimum raw sensor value
sensor_max = 65535    # Maximum raw sensor value (for a 16-bit ADC)
sound_min_dB = 30    # Minimum sound level in dB (corresponding to sensor_min)
sound_max_dB = 120    # Maximum sound level in dB (corresponding to sensor_max)
sensor_calibration = 1  # Example calibration factor (adjust according to your sensor)


################ MQ6 SENSOR CONFIG ######################
RO_CLEAN_AIR_FACTOR = 3.59
CALIBRATION_SAMPLE_TIMES = 20
CALIBRATION_SAMPLE_INTERVAL = 100
R0_RATIO_BENZENE = 4
R0_RATIO_CO2 = 60
R0_RATIO_CO = 4.5
R0_RATIO_NH4 = 3.5
analog_pin = machine.ADC(26)
analog_pin_mq135 = machine.ADC(29)


################ DUST SENSOR CONFIG ##############################
SENSOR_PIN = 28  # Analog pin connected to the sensor
LED_PIN = 2      # Digital pin connected to an LED for indication


################ GPS MODULE CONFIG #############################
latitude = ""
longitude = ""
satellites = ""
def gps_measure_second_core():
    from machine import Pin, UART
    import utime, time
    gps_module = machine.UART(0, baudrate=9600, tx=machine.Pin(12), rx=machine.Pin(13))
    buff = bytearray(255)       # Used to Store NMEA Sentences
    TIMEOUT = False
    FIX_STATUS = False
    latitude = ""
    longitude = ""
    satellites = ""
    def get_position_data(gps_module):
        global FIX_STATUS, TIMEOUT, latitude, longitude, satellites
        timeout = time.time() + 20  # 20 seconds from now+
        while True:
            line = gps_module.readline()
            if line is not None:
                if line.startswith(b'$GPGGA'):
                    parts = line.split(b',')
                    if len(parts) == 15:
                        if (
                            parts[1]
                            and parts[2]
                            and parts[3]
                            and parts[4]
                            and parts[5]
                            and parts[6]
                            and parts[7]
                        ):
                            latitude = convert_to_degrees(parts[2].decode())
                            if parts[3] == b'S':
                                latitude = -latitude
                            longitude = convert_to_degrees(parts[4].decode())
                            if parts[5] == b'W':
                                longitude = -longitude
                            satellites = parts[7].decode()
                            gpsTime = parts[1][0:2].decode() + ":" + parts[1][2:4].decode() + ":" + parts[1][4:6].decode()
                            FIX_STATUS = True
                            break
            if time.time() > timeout:
                TIMEOUT = True
                break
            print("Connecting to GPS ")
            utime.sleep_ms(1000)
    def convert_to_degrees(raw_degrees):
        raw_as_float = float(raw_degrees)
        first_digits = int(raw_as_float / 100)  # degrees
        next_two_digits = raw_as_float - float(first_digits * 100)  # minutes
        converted = float(first_digits + next_two_digits / 60.0)
        converted = '{0:.6f}'.format(converted)  # to 6 decimal places
        return str(converted)
    while True:
        get_position_data(gps_module)

        if FIX_STATUS:
            print("fix......")
            print(latitude)
            print(longitude)
            print(satellites)
            
            FIX_STATUS = False
            
        if TIMEOUT:
            print("Request Timeout: No GPS data is found.")
            TIMEOUT = False
#####  GPS SENSOR FUNCTIONS END ######

##### SECOND CORE START #####
def start_measurement_thread():
    _thread.start_new_thread(gps_measure_second_core,())
    print("Entered second core")
##### SECOND CORE END #####
start_measurement_thread()

#####  MQ6 SENSOR FUNCTIONS START ######
def calibrate_mq6():
    print("Calibrating...")
    val = 0.0
    for _ in range(CALIBRATION_SAMPLE_TIMES):
        val += analog_pin.read_u16()
        time.sleep_ms(CALIBRATION_SAMPLE_INTERVAL)
    val /= CALIBRATION_SAMPLE_TIMES
    val = val / 65535 * 3.3
    global RO_CLEAN_AIR_FACTOR
    RO_CLEAN_AIR_FACTOR = val
    print("Calibration complete. RO_CLEAN_AIR_FACTOR is", RO_CLEAN_AIR_FACTOR)
def read_R0():
    val = 0.0
    for _ in range(CALIBRATION_SAMPLE_TIMES):
        val += analog_pin.read_u16()
        time.sleep_ms(CALIBRATION_SAMPLE_INTERVAL)
    val /= CALIBRATION_SAMPLE_TIMES
    val = val / 65535 * 3.3
    RS_RO = val / RO_CLEAN_AIR_FACTOR
    return RS_RO
def calculate_benzene_concentration(RS_RO):
    benzene_concentration = (R0_RATIO_BENZENE / RS_RO - 1) / 10
    return benzene_concentration
def read_mq6_sensor():
    RS_RO_benzene = analog_pin.read_u16() / 65535 * 3.3 / read_R0()
    benzene_conc = calculate_benzene_concentration(RS_RO_benzene)
    return benzene_conc if benzene_conc else None
#####  MQ6 SENSOR FUNCTIONS END ######


def calibrate_mq135():
    print("Calibrating MQ135...")
    val = 0.0
    for _ in range(CALIBRATION_SAMPLE_TIMES):
        val += analog_pin_mq135.read_u16()
        time.sleep_ms(CALIBRATION_SAMPLE_INTERVAL)
    val /= CALIBRATION_SAMPLE_TIMES
    val = val / 65535 * 3.3  # Convert to voltage
    global RO_CLEAN_AIR_FACTOR
    RO_CLEAN_AIR_FACTOR = val
    print("Calibration complete. RO_CLEAN_AIR_FACTOR is", RO_CLEAN_AIR_FACTOR)
def read_R0_mq135():
    val = 0.0
    for _ in range(CALIBRATION_SAMPLE_TIMES):
        val += analog_pin_mq135.read_u16()
        time.sleep_ms(CALIBRATION_SAMPLE_INTERVAL)
    val /= CALIBRATION_SAMPLE_TIMES
    val = val / 65535 * 3.3
    RS_RO = val / RO_CLEAN_AIR_FACTOR
    return RS_RO
def calculate_concentration_mq135(RS_RO, R0_RATIO):
    concentration = (R0_RATIO / RS_RO - 1) / 10
    return concentration
def read_mq135_sensor():
    RS_RO_CO2 = analog_pin.read_u16() / 65535 * 3.3 / (R0_RATIO_CO2 * read_R0_mq135())
    RS_RO_CO = analog_pin.read_u16() / 65535 * 3.3 / (R0_RATIO_CO * read_R0_mq135())
    RS_RO_NH4 = analog_pin.read_u16() / 65535 * 3.3 / (R0_RATIO_NH4 * read_R0_mq135())

    concentration_CO2 = calculate_concentration_mq135(RS_RO_CO2, R0_RATIO_CO2)
    concentration_CO = calculate_concentration_mq135(RS_RO_CO, R0_RATIO_CO)
    concentration_NH4 = calculate_concentration_mq135(RS_RO_NH4, R0_RATIO_NH4)
    print("concentration_CO2:",concentration_CO2,"  concentration_CO:",concentration_CO,"  concentration_NH3:",concentration_NH4)

    return [concentration_CO2,concentration_CO,concentration_NH4]



#####  LDR SENSOR FUNCTIONS START ######
def read_ldr_sensor():
    pin_ldr=16
    pin = machine.Pin(pin_ldr, machine.Pin.IN)
    A=pin.value()
    if A:
        print("LOW")
        return "LOW"
    else:
        print("HIGH")
        return "HIGH"
        
#####  LDR SENSOR FUNCTIONS END ######



#####  NOISE SENSOR FUNCTIONS START ######
def map_sensor_to_dB(sensor_value):
    normalized_value = (sensor_value - sensor_min) / (sensor_max - sensor_min)
    sound_level_dB = (normalized_value * (sound_max_dB - sound_min_dB)) + sound_min_dB
    sound_level_dB = sound_level_dB * sensor_calibration  
    return sound_level_dB
def read_noise_sensor():
    sensor_value = noise_sensor.read_u16()
    sound_level_dB = map_sensor_to_dB(sensor_value)
    print(f"Sound Level: {sound_level_dB:.2f} dB")
    return sound_level_dB
#####  NOISE SENSOR FUNCTIONS END ######
   
     
#####  DUST SENSOR FUNCTIONS START ######
def calibrate_dust():
    import machine
    global adc, led
    adc = machine.ADC(SENSOR_PIN)
    led = machine.Pin(LED_PIN, machine.Pin.OUT)
    print("Setup completed")
def read_dust_sensor():
    sensor_value = adc.read_u16()  # Read the sensor value
    voltage = sensor_value * (5.0 / 65535.0)  # Convert sensor value to voltage
    density = voltage_to_dust_density(voltage)  # Convert voltage to dust density
    print("Sensor Value:", sensor_value, "\tVoltage:", voltage, "V\tDust Density:", density, "ug/m3")
    return density
    if density > 50:  # Example threshold for LED indication
        led.value(0)
    else:
        led.value(1)
def voltage_to_dust_density(voltage):
    a = 0.17  # Coefficient 'a' from datasheet
    b = 0.0084  # Coefficient 'b' from datasheet
    density = (voltage - b) / a
    return density
#####  DUST SENSOR FUNCTIONS END ######


com1 = Easy_comms(uart_id=0, baud_rate=9600)
#com1.start()
count = 0

bl=Pin(25,Pin.OUT)
bl.high()
calibrate_mq6()
calibrate_mq135()
calibrate_dust()
while True:
    message = com1.read()
    if message is not None:
        #NOISE SENSOR
        A=read_noise_sensor()
        #sleep(1)
        #LDR SENSOR
        B=read_ldr_sensor()
        #sleep(1)
        #DUST SENSOR
        C=read_dust_sensor()
        #sleep(1)
        #MQ6 SENSOR
        D=read_mq6_sensor()
        #sleep(1)
        E=read_mq135_sensor()
        #GPS SENSOR
        #read_gps_sensor()
        LIST=f"gps_latitude:{latitude},gps_longitude:{longitude},noise_data:{A},ldr_data:{B},dust_sensor:{C},mq6_benzene_data:{D},mq135_CO2_data:{E[0]},mq135_CO_data:{E[1]},mq135_NH3_data:{E[2]}"
        com1.send(str(LIST))