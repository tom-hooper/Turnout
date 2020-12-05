#!/usr/bin/python

'''

!! This requires a recent build of Multimon-NG as the old builds wont accept a piped input !!

Change the rtl_fm string to suit your needs.. add -a POCSAG512 , 2400 etc if needed to the Multimon-ng string
This just prints and writes to a file, you can put it in a threaded class and pass though a queue
or whatever suits your needs.


'''
import time
import sys
import subprocess
import os
import re

def curtime():
    return time.strftime("%H:%M:%S %Y-%m-%d")

with open('error.txt','a') as file:
    file.write(('#' * 20) + '\n' + curtime() + '\n')

multimon_ng = subprocess.Popen("rtl_fm -f 148.9125M -s 22050 | multimon-ng -t raw \
                                -a POCSAG512 -a POCSAG1200 -a POCSAG2400 \
                                -e -f alpha /dev/stdin -",
                               #stdin=rtl_fm.stdout,
                               stdout=subprocess.PIPE,
                               stderr=open('error.legal','a'),
                               shell=True)

try:
    while True:
        line = multimon_ng.stdout.readline()
        multimon_ng.poll()
        #print(line)
        if line.__contains__(b'Alpha:'):    # filter out only the alpha
            if line.startswith(b'POCSAG'):
                address = line[22:28].replace(b" ", b"").zfill(7)
                message = line.split(b'Alpha:   ')[1]
                message = re.sub(b'(<NUL>)',b'', message.rstrip())
                output=(address+b' '+ message+b'\n')
                print(address, curtime(), message)
                with open('pocsag.txt','ab') as f:
                    f.write(output)
                    #f.write(line)
        if not b'Alpha:' in line:
            with open("missed.txt","ab") as missed:
                missed.write(line + b'\n')

except KeyboardInterrupt:
    os.kill(multimon_ng.pid, 9)




#from rtlsdr import RtlSdr
#import asyncio
#async def streaming():
#    sdr = RtlSdr()
#
#    # configure device
#    sdr.sample_rate = 2.048e6  # Hz
#    sdr.center_freq = 148912500     # Hz
#    sdr.freq_correction = 10   # PPM
#    sdr.gain = 'auto'
#    async for samplen in sdr.stream():
#        multimon-ng -t raw -a POCSAG512 -a POCSAG1200 -a POCSAG2400 -a scope


#print(sdr.read_samples(512))
#test
