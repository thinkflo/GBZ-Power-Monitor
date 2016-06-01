#!/usr/bin/env python2.7
# date: 30/05/16
# author: Popcorn <abandonedemails@gmail.com> - Add "Sudomod" in the subject or your message will not be received
# version: 1.1
# name: GBZ-Power-Monitor - a Power Management utility for the Gameboy Zero project
# description: a GPIO monitor that detects low battery and power switch status which provides a graceful shutdown facility
# source: https://github.com/NullCorn/GBZ-Power-Monitor/

import RPi.GPIO as GPIO
import ConfigParser
import logging
import subprocess
import threading
import sys
import time

# Requre values
try:
    config = ConfigParser.SafeConfigParser()
    config.read('gbz_power_monitor.ini')
except ConfigParser.ParsingError, err:
    print 'Could not parse:', err

def initGPIO():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(batteryGPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(powerGPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def batteryState(arg):
    
    while not arg['stop']:
        logging.debug('Launch Battery Polling Worker')
        batteryState = 0 
        sampleRate = 0.1    

        for bounceSample in range(1, int(round(float(config.get('gbz_power_monitor','batterySample')) / sampleRate))):
            time.sleep(sampleRate)

            batteryState = {
                0 : lambda batteryState: batteryState + 1,
                1 : lambda batteryState: batteryState - 1
            }[GPIO.input(config.get('gbz_power_monitor','batteryGPIO'))](batteryState)
    
        if batteryState is int(round(float(config.get('gbz_power_monitor','batterySample')) / sampleRate)) - 1:
            logging.debug('Solid Low Battery condition detected')

            shutdownVideo = subprocess.Popen("/usr/bin/omxplayer --no-osd --layer 999999 " + config.get('gbz_power_monitor','shutdownVideo') + " --alpha 180", shell=True)
            shutdownVideo.wait()
            if shutdownVideo.returncode is 0:
                shutdownProcess = subprocess.Popen("sudo shutdown -h now", shell=True)
                arg['stop'] = True

        if float(batteryState) > 0:
            logging.debug('Triggered Low Battery Warning')
            lowBatteryAlertVideo = subprocess.Popen("/usr/bin/omxplayer --no-osd --layer 999999 " + config.get('gbz_power_monitor','lowalertVideo') + " --alpha 160;", shell=True)
            
            #Discovered a bug with the Python GPIO library and threaded events.  Need to unbind and rebind after a System Call or the program will crash
            GPIO.remove_event_detect(batteryGPIO)
            GPIO.add_event_detect(batteryGPIO, GPIO.BOTH, callback=lowBattery, bouncetime=300)
            
        if batteryState * -1 is int(round(float(config.get('gbz_power_monitor','batterySample')) / sampleRate)) - 1:
            logging.debug('Good Battery condition restored')
            logging.debug('Exit Battery Polling worker')
            shutdownProcess.kill()
            shutdownVideo.kill()
            lowBatteryAlertVideo.kill()
            arg['stop'] = True

        print batteryState
        
def powerSwitch(channel):
    #Checking for LED bounce for the duration of the Power Timeout
    for bounceSample in range(1, int(round(powerTimeout / sampleRate))):
        time.sleep(sampleRate)

        if GPIO.input(powerGPIO) is 1:
            break

    if bounceSample is int(round(powerTimeout / sampleRate)) - 1:
    #When the Power Switch is placed in the off position with no bounce for the duration of the Power Timeout, we immediately shutdown
    shutdownProcess = subprocess.Popen("sudo shutdown -h now", shell=True)
    
    try:
        sys.stdout.close()
    except:
        pass
        
    try:
        sys.stderr.close()
    except:
        pass

      sys.exit(0)

def lowBattery(channel):
    thread = threading.Thread(target=batteryState, args=(info,))
    thread.start()
    while True:
        try:
            logging.debug('Hello from main')
            time.sleep(1)
        except KeyboardInterrupt:
            info['stop'] = True
            break
    thread.join()
        
def main():
    logging.basicConfig(level=logging.DEBUG, format='%(relativeCreated)6d %(threadName)s %(message)s')
    info = {'stop': False}
    
    #if the Low Battery LED is active when the program launches, handle it 
    if GPIO.input(batteryGPIO) is 0:
        lowBattery(batteryGPIO)

    #if the Power Switch is active when the program launches, handle it
    if GPIO.input(powerGPIO) is 0:
        powerSwitch(powerGPIO)
    
    try:
        GPIO.remove_event_detect(batteryGPIO)
        GPIO.add_event_detect(batteryGPIO, GPIO.FALLING, callback=lowBattery, bouncetime=300)

        GPIO.remove_event_detect(powerGPIO)
        GPIO.add_event_detect(powerGPIO, GPIO.FALLING, callback=powerSwitch, bouncetime=300)
      except KeyboardInterrupt:
        GPIO.cleanup()

if __name__ == '__main__':
    main()
