import time
import pyb

S = pyb.ADC('P6') # P8 Capteur de distances

#Boucle tant que avec calule de mesure de distance
dist=0
while(True):
    #d = (1/(S.read() + 0.42)*10000)
    #print(d,'cm')
    dist=0
    for i in range(400):
        dist = dist + S.read()
        time.sleep_ms(5)
    print(dist/400)
