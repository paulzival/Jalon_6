import sensor, image, time, pyb
from pyb import LED, Pin


class EtatRobot:
    RECHERCHE = 0    # État de recherche de la balle (balayage)
    SUIVI = 1        # État de suivi de la balle
    FOURCHE = 2      # État : balle dans la fourche

etat = EtatRobot.RECHERCHE  # État initial : recherche de la balle


# Initialisation du capteur de caméra
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.set_vflip(True)
sensor.set_hmirror(True)
sensor.skip_frames(time=200)

# Seuils LAB pour la balle rouge (inchangés)
thresholdsRedBall = (0, 100, 47, 87, 16, 68)

# Configuration des broches pour les moteurs
p4 = pyb.Pin('P4', pyb.Pin.OUT_PP, pyb.Pin.PULL_NONE)
p5 = pyb.Pin('P5', pyb.Pin.OUT_PP, pyb.Pin.PULL_NONE)
p7 = pyb.Pin('P7', pyb.Pin.OUT_PP, pyb.Pin.PULL_NONE)
p8 = pyb.Pin('P8', pyb.Pin.OUT_PP, pyb.Pin.PULL_NONE)
LED_R = LED(1)
LED_V = LED(2)

# capteur de fourche
Cd = Pin('P8', Pin.IN)   # Capteur de fourche

# Configuration des timers et canaux PWM
tim12 = pyb.Timer(2, freq=100)
tim2X = pyb.Timer(4, freq=100)

# Canaux PWM pour les moteurs
M11 = tim12.channel(3, pyb.Timer.PWM, pin=p5)  # Moteur droit avant
M12 = tim12.channel(4, pyb.Timer.PWM, pin=p4)  # Moteur droit arrière
M2X = tim2X.channel(1, pyb.Timer.PWM, pin=p7)  # Moteur de direction

tim12.freq(100)
tim2X.freq(100)

# Variables globales pour le balayage et l'état
scanning = False
etat = 0  # 0: recherche, 1: suivi, 2: balle dans fourche

def cmd_moteur(rapport_av_ar, vit_droite, vit_gauche):
    """Commande les moteurs avec les vitesses spécifiées."""
    M2X.pulse_width_percent(rapport_av_ar)
    M11.pulse_width_percent(vit_droite)
    M12.pulse_width_percent(vit_gauche)

def suivre_balle(blob_cx, blob_cy, img_width):
    centre_x = img_width // 2
    delta_x = centre_x - blob_cx

    # Ajustement de la vitesse en fonction de la distance verticale
    if blob_cy > 180:  # Balle très proche
        vitesse_base = 30
    elif blob_cy < 80:  # Balle loin
        vitesse_base = 80
    else:
        vitesse_base = 60

    # Ajustement de la rotation
    ajustement_rotation = min(30, abs(delta_x) // 6)

    if delta_x < 0:  # balle à droite
        vit_droite = max(20, vitesse_base - ajustement_rotation)
        vit_gauche = min(100, vitesse_base + ajustement_rotation)
    elif delta_x > 0:  # balle à gauche
        vit_droite = min(100, vitesse_base + ajustement_rotation)
        vit_gauche = max(20, vitesse_base - ajustement_rotation)
    else:  # balle centrée
        vit_droite = vit_gauche = vitesse_base

    cmd_moteur(0, vit_droite, vit_gauche)


def scan_for_ball():    #cherche la balle
    if scanning:
        cmd_moteur(0, 60, 00)  # Tourner à droite

def stop_moteurs(): # arrét des moteur
    cmd_moteur(0, 0, 0)



clock = time.clock()

while True:
    clock.tick()
    img = sensor.snapshot()

    # Zone de detection de terrain
    Zone_Detect = (0, 50, img.width(), 200)  # (x, y, width, height)

    # Vérifier si la balle est dans la fourche
    if Cd.value() == 1:
        etat = EtatRobot.FOURCHE
        print("Balle dans la fourche")
        stop_moteurs()
        LED_V.off()
        LED_R.on()
    else:
        # Recherche des blobs dans la ROI
        blobs = img.find_blobs([thresholdsRedBall], area_threshold=50, merge=False, roi=Zone_Detect)
    if len (blobs)!=0:
            # Trouver le plus grand blob (balle)
            largest_blob = blobs[-1]
            img.draw_rectangle(largest_blob.rect(), color=(0, 255, 0))
            img.draw_cross(largest_blob.cx(), largest_blob.cy(), color=(0, 255, 0))
            etat = EtatRobot.SUIVI # Suivi de la balle
            suivre_balle(largest_blob.cx(), largest_blob.cy(), img.width())
            # Allumer la LED verte si la balle est détectée
            LED_R.off()
            LED_V.on()
            print("Balle détectée")
    else:
            etat = EtatRobot.RECHERCHE
            # Activer le balayage si aucune balle n'est détectée
            if not scanning:
                scanning = True
            scan_for_ball()

            # Allumer la LED rouge si aucune balle n'est détectée
            LED_V.off()
            LED_R.on()
            print("Balle non détectée")

    #Gestion des état   
    if etat == EtatRobot.FOURCHE:
        stop_moteurs()
    elif etat == EtatRobot.SUIVI:
        pass  # La logique de suivi est déjà gérée ci-dessus
    elif etat == EtatRobot.RECHERCHE:
        pass  # La logique de recherche est déjà gérée ci-dessus

    pyb.delay(10)
    print("FPS:", clock.fps())
