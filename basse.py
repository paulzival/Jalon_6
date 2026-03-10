import sensor, image, time, pyb
from pyb import LED, Pin

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

def follow_ball(blob_cx, blob_cy, img_width):
    """Suivre la balle en ajustant la vitesse des moteurs."""
    global scanning

    # Calcul de l'erreur horizontale
    delta = 160 - blob_cx

    # Ajustement de la vitesse en fonction de la position verticale (Cy)
    speed_adjust_cy = 60 - (blob_cy // 12)

    # Ajustement de la vitesse en fonction de l'erreur horizontale (delta)
    speed_adjust_delta_right = 70 + (delta // 4)
    speed_adjust_delta_left = 70 - (delta // 4)

    # Limiter les vitesses pour éviter les valeurs extrêmes
    vit_droite = min(max(20, speed_adjust_delta_right + speed_adjust_cy), 100)
    vit_gauche = min(max(20, speed_adjust_delta_left + speed_adjust_cy), 100)

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

    # Définir une zone d'intérêt (ROI) pour limiter la détection à une certaine partie de l'image
    Hauteur_detect = (0, 50, img.width(), 200)  # (x, y, width, height) - ajuste ces valeurs selon ton besoin

    # Vérifier si la balle est dans la fourche
    if Cd.value() == 1:
        etat = 2  # Balle dans la fourche
        print('Balle dans la fourche')
        stop_moteurs()
    else:

        print('Balle pas là')
        etat = 0  # Retour à l'état de recherche si aucune balle dans la fourche

    # Gestion des états
    if etat == 2:
        stop_moteurs()
    else:
        # Recherche des blobs correspondant à la balle rouge dans la ROI
        blobs = img.find_blobs([thresholdsRedBall], area_threshold=50, merge=False, roi=Hauteur_detect)

        if blobs:
            # Trouver le plus grand blob (balle)
            largest_blob = blobs[-1]
            img.draw_rectangle(largest_blob.rect(), color=(0, 255, 0))
            img.draw_cross(largest_blob.cx(), largest_blob.cy(), color=(0, 255, 0))
            etat = 1  # Suivi de la balle
            follow_ball(largest_blob.cx(), largest_blob.cy(), img.width())
        else:
            etat = 0  # Recherche de la balle
            # Activer le balayage si aucune balle n'est détectée ♀ß
            if not scanning:
                scanning = True

            scan_for_ball()

        if len(blobs) > 0:
            LED_R.off();
            LED_V.on();
            print ('Balle la ')
        elif (Cd.value()==0):
            LED_V.off();
            LED_R.on();
            print ('Balle pas la ')
    pyb.delay(10)
    print(clock.fps())
