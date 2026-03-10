import time
import pyb
# Appel du pin pour le capteur de distance
S = pyb.ADC('P6') # P8 Capteur de distances

#Boucle tant que avec calule de mesure de distance
while(True):

    d = (961259*((S.read())**(-1.48))+4)
    # Affichage des mesures en cm
    print("{:.2f} cm".format(d))
    time.sleep_ms(100)
