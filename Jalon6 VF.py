import sensor, image, time, pyb
from pyb import LED, Pin

# --- Initialisation matérielle ---
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)  # Résolution réduite pour gagner en performance
sensor.set_vflip(True)
sensor.set_hmirror(True)
sensor.skip_frames(time=100)  # Temps réduit

# Seuils LAB
thresholds_rouge = (0, 100, 47, 87, 16, 68)  # Balle rouge
thresholds_bleu = (0, 100, -128, 127, -29, -2)  # Sol bleu

# Broches
LED_R = LED(1)
LED_V = LED(2)
Capteur = pyb.ADC('P6')  # Capteur de distance
Buzzr = Pin('P9', Pin.OUT)
Cd = Pin('P8', Pin.IN)    # Capteur de fourche
code = 1
# Moteurs (PWM)
tim12 = pyb.Timer(2, freq=100)
tim2X = pyb.Timer(4, freq=100)
M11 = tim12.channel(3, pyb.Timer.PWM, pin=pyb.Pin('P5', pyb.Pin.OUT_PP))
M12 = tim12.channel(4, pyb.Timer.PWM, pin=pyb.Pin('P4', pyb.Pin.OUT_PP))
M2X = tim2X.channel(1, pyb.Timer.PWM, pin=pyb.Pin('P7', pyb.Pin.OUT_PP))

# Variables globales
etat = "recherche"

# --- Fonctions ---
def cmd_moteur(av_ar,mg,md):
    M2X.pulse_width_percent(av_ar)
    M11.pulse_width_percent(mg)
    M12.pulse_width_percent(md)

def arreter_moteurs():
    cmd_moteur(0,0,0)

def suivre_balle(blob_cx, blob_cy, img_width):
    centre_x = img_width // 2
    delta_x = centre_x - blob_cx
    vitesse_base = 30 if blob_cy > 180 else (80 if blob_cy < 80 else 60)
    ajustement = min(30, abs(delta_x) // 6)
    if delta_x < 0:  # Balle à droite
        cmd_moteur(0,max(20, vitesse_base - ajustement),min(100, vitesse_base + ajustement))

    elif delta_x > 0:  # Balle à gauche
        M11.pulse_width_percent(min(100, vitesse_base + ajustement))
        M12.pulse_width_percent(max(20, vitesse_base - ajustement))
    else:  # Balle centrée
        M11.pulse_width_percent(vitesse_base)
        M12.pulse_width_percent(vitesse_base)

def chercher_balle():
    if code == 1:
       cmd_moteur(0,70,0)
    if code == 2:
       cmd_moteur(0,0,70)


def chercher_sol_bleu(img):
    global etat, code
    # Divise l'écran en deux
    blobs_bleus = img.find_blobs([thresholds_bleu])
    if blobs_bleus:
      # tris de la taille des blobs
        largest_blue = blobs_bleus[-1]

        # Affiche infos bug
        print("Blob bleu : cx={}, cy={}, pixels={}".format(largest_blue.cx(), largest_blue.cy(), largest_blue.pixels()))

        # Compare la position du blob par rapport au centre
        if largest_blue.cx() > img.width() // 2 + 20:  # +20 pour éviter les erreurs de détection au centre
            code = 2  # Tourne à gauche (moteur droit actif)
            cmd_moteur(0, 70, 0)
            time.sleep_ms(1200)
        else:
            code = 1  # Tourne à droite (moteur gauche actif)
            cmd_moteur(0, 0, 70)
            time.sleep_ms(1200)

        time.sleep_ms(500)
        arreter_moteurs()
        etat = "recherche"  # Retour à la recherche après ajustement

    else:
        chercher_balle()
        time.sleep_ms(200)

# --- Boucle principale ---
clock = time.clock()
while True:
    img = sensor.snapshot()
    Dist = 961259 * (Capteur.read() ** -1.48) + 4  # Calcul de la distance

    # Détection des éléments (une seule fois par boucle)
    Recherche_rouge = img.find_blobs([thresholds_rouge], roi=(0, 50, img.width(), 150))
    Recherche_bleu = img.find_blobs([thresholds_bleu], roi=(0, img.height()//2, img.width(), img.height()//2)) if etat == "recherche_bleu" else None

    # Mise à jour de l'état (priorité : fourche > mur > suivre > recherche)
    if Cd.value() == 1:
        etat = "fourche"
    elif Dist < 12 and etat != "recherche_bleu":  # Priorité absolue au mur sauf si déjà en recherche_bleu
        etat = "mur"
    elif Recherche_rouge and etat != "recherche_bleu":
        etat = "suivre"
    else:
        etat = "recherche" if etat != "recherche_bleu" else "recherche_bleu"

    # Actions selon l'état
    if etat == "fourche":
        arreter_moteurs()
        Buzzr.low()
        LED_R.off()
        LED_V.on()
    elif etat == "mur":
        Buzzr.high()
        arreter_moteurs()
        M2X.pulse_width_percent(100)  # Reculer
        M11.pulse_width_percent(10)
        M12.pulse_width_percent(10)
        time.sleep_ms(500)
        arreter_moteurs()
        etat = "recherche_bleu"  # Priorité : chercher le sol bleu
    elif etat == "suivre" and Recherche_rouge:
        largest_blob = max(Recherche_rouge, key=lambda b: b.pixels())
        suivre_balle(largest_blob.cx(), largest_blob.cy(), img.width())
        LED_R.off()
        LED_V.on()
    elif etat == "recherche_bleu":
        Buzzr.low()
        chercher_sol_bleu(img)
        LED_R.on()
        LED_V.off()

    elif etat == "recherche":
        chercher_balle()
        LED_R.on()
        LED_V.off()

    Buzzr.low()  # Désactive le buzzer par défaut
    time.sleep_ms(50)  # Réduit la charge CPU
    print("FPS: {:.1f}, Etat: {}, Dist: {:.1f} cm".format(clock.fps(), etat, Dist))

