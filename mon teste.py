import sensor, image, time, pyb
from pyb import LED, Pin

# Initialisation du capteur de caméra
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.set_vflip(True)
sensor.set_hmirror(True)
sensor.skip_frames(time=200)

# Seuils LAB pour la balle rouge et bleue
thresholdsRedBall = (0, 100, 47, 87, 16, 68)
thresholds_bleu = (0, 100, -128, 127, -29, -2)

# Configuration des broches pour les moteurs et capteurs
p4 = pyb.Pin('P4', pyb.Pin.OUT_PP, pyb.Pin.PULL_NONE)
p5 = pyb.Pin('P5', pyb.Pin.OUT_PP, pyb.Pin.PULL_NONE)
p7 = pyb.Pin('P7', pyb.Pin.OUT_PP, pyb.Pin.PULL_NONE)
p8 = pyb.Pin('P8', pyb.Pin.OUT_PP, pyb.Pin.PULL_NONE)
LED_R = LED(1)
LED_V = LED(2)
Capteur = pyb.ADC('P6')  # Capteur de distances
Buzzr = Pin('P9', Pin.OUT)
Cd = Pin('P8', Pin.IN)    # Capteur de fourche

# Configuration des timers et canaux PWM
tim12 = pyb.Timer(2, freq=100)
tim2X = pyb.Timer(4, freq=100)
M11 = tim12.channel(3, pyb.Timer.PWM, pin=p5)  # Moteur droit avant
M12 = tim12.channel(4, pyb.Timer.PWM, pin=p4)  # Moteur droit arrière
M2X = tim2X.channel(1, pyb.Timer.PWM, pin=p7)  # Moteur de direction

# Variables globales
etat = "recherche"
scanning = False 

def cmd_moteur(rapport_av_ar, vit_droite, vit_gauche):
    M2X.pulse_width_percent(rapport_av_ar)
    M11.pulse_width_percent(vit_droite)
    M12.pulse_width_percent(vit_gauche)

def follow_ball(blob_cx, blob_cy, img_width):
    centre_x = img_width // 2
    delta_x = centre_x - blob_cx
    if blob_cy > 180:  # Balle très proche
        vitesse_base = 30
    elif blob_cy < 80:  # Balle loin
        vitesse_base = 80
    else:
        vitesse_base = 60
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

def evite_mure(blob_cx, blob_cy, img_width):
    if largest_blue_blob.cx() < img.width() // 2:
        cmd_moteur(0, -80, 80)  # Tourner à gauche
    else:
        cmd_moteur(0, 80, -80)  # Tourner à droite


def scan_for_ball():
    cmd_moteur(0, 60, 0)

def stop_moteurs():
    cmd_moteur(0, 0, 0)

clock = time.clock()

while True:
    img = sensor.snapshot()
    Hauteur_detect = (0, 50, img.width(), 200)

    # Détection des éléments
    Recherche_B = img.find_blobs([thresholdsRedBall], roi=Hauteur_detect)
    Dist = 961259 * ((Capteur.read()) ** (-1.48)) + 4

    # Détection du sol
    blobs_bleus = img.find_blobs([thresholds_bleu], area_threshold=50)


    # Affichage de la distance en temps réel
    print("Distance: {:.1f} cm".format(Dist))

    # Mise à jour de l'état
    if Cd.value() == 1:
        etat = "fourche"
    elif Dist < 12:
        etat = "mur"
    elif Recherche_B:
        etat = "suivre"
    else:
        etat = "recherche"

    # Actions selon l'état
    if etat == "fourche":
        stop_moteurs()
        Buzzr.low()

    elif etat == "mur":
        Buzzr.high()
        cmd_moteur(100, 10, 10)  # Reculer
        time.sleep_ms(500)
        stop_moteurs()
        etat = "recherche_bleu"

    elif etat == "suivre":
        largest_blob = max(Recherche_B, key=lambda b: b.pixels())
        follow_ball(largest_blob.cx(), largest_blob.cy(), img.width())

    elif etat == "recherche_bleu":
        Buzzr.low()
        if blobs_bleus:
            largest_blue_blob = max(blobs_bleus, key=lambda b: b.pixels())
            evite_mure(largest_blob.cx(), largest_blob.cy(), img.width())
    
    
    elif etat == "recherche":
        if not scanning:
            scanning = True
            scan_for_ball()


        time.sleep_ms(500)
        stop_moteurs()
        etat = "recherche"  # Retourne en mode recherche après avoir cherché le bleu

    # Gestion des LEDs
    if Recherche_B:
        LED_R.off()
        LED_V.on()
    else:
        LED_R.on()
        LED_V.off()

    Buzzr.low()  # Désactive le buzzer par défaut
    pyb.delay(10)
    print("FPS: {:.1f}".format(clock.fps()))
