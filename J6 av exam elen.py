import sensor, image, time, pyb
from pyb import LED, Pin

# --- Initialisation matérielle ---
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.set_vflip(True)
sensor.set_hmirror(True)
sensor.skip_frames(time=100)

# Seuils LAB
thresholds_rouge = (0, 100, 47, 87, 16, 68)  # Balle rouge
thresholds_bleu = (0, 100, -128, 127, -29, -2)  # Sol bleu

# Broches
LED_R = LED(1)
LED_V = LED(2)
Capteur = pyb.ADC('P6')  # Capteur de distance
Buzzr = Pin('P9', Pin.OUT)
Cd = Pin('P8', Pin.IN)    # Capteur de fourche
code = 1  # 1 = gauche, 2 = droite

# Moteurs (PWM)
tim12 = pyb.Timer(2, freq=100)
tim2X = pyb.Timer(4, freq=100)
M11 = tim12.channel(3, pyb.Timer.PWM, pin=pyb.Pin('P5', pyb.Pin.OUT_PP))
M12 = tim12.channel(4, pyb.Timer.PWM, pin=pyb.Pin('P4', pyb.Pin.OUT_PP))
M2X = tim2X.channel(1, pyb.Timer.PWM, pin=pyb.Pin('P7', pyb.Pin.OUT_PP))

# Variables globales
etat = "recherche"

# --- Fonctions ---
def cmd_moteur(av_ar, mg, md):
    M2X.pulse_width_percent(av_ar)
    M11.pulse_width_percent(mg)
    M12.pulse_width_percent(md)

def arreter_moteurs():
    cmd_moteur(0, 0, 0)

def suivre_balle(blob_cx, blob_cy, img_width):
    centre_x = img_width // 2
    delta_x = centre_x - blob_cx
    vitesse_base = max(50, 30 if blob_cy > 180 else (80 if blob_cy < 80 else 60))
    ajustement = min(30, abs(delta_x) // 6)
    if delta_x < 0:  # Balle à droite
        cmd_moteur(0, max(50, vitesse_base - ajustement), min(100, vitesse_base + ajustement))
    elif delta_x > 0:  # Balle à gauche
        cmd_moteur(0, min(100, vitesse_base + ajustement), max(50, vitesse_base - ajustement))
    else:  # Balle centrée
        cmd_moteur(0, vitesse_base, vitesse_base)

def chercher_balle():
    if code == 1:
        cmd_moteur(0, 70, 0)  # Tourne à droite (moteur gauche actif)
    if code == 2:
        cmd_moteur(0, 0, 70)  # Tourne à gauche (moteur droit actif)

def chercher_sol_bleu(img):
    global etat, code
    blobs_bleus = img.find_blobs([thresholds_bleu])
    if blobs_bleus:
        blobs_bleus.sort(key=lambda b: b.pixels(), reverse=True)  # Tri par taille décroissante
        largest_blue = blobs_bleus[-1]  # Prend le plus gros
        if largest_blue.cx() > img.width() // 2:  # Blob bleu à droite
            code = 2  # Tourne à gauche
            cmd_moteur(0, 70, 0)
            time.sleep_ms(500)
        else:  # Blob bleu à gauche
            code = 1  # Tourne à droite
            cmd_moteur(0, 0, 70)
            time.sleep_ms(500)
        etat = "recherche"  # Retour à la recherche après ajustement

# --- Boucle principale ---
clock = time.clock()
while True:
    img = sensor.snapshot()
    Dist = 961259 * (Capteur.read() ** -1.48) + 4  # Calcul de la distance

    # Détection des éléments
    Recherche_rouge = img.find_blobs([thresholds_rouge], roi=(0, 50, img.width(), 150))
    Recherche_bleu = img.find_blobs([thresholds_bleu], roi=(0, img.height()//2, img.width(), img.height()//2)) if etat == "recherche_bleu" else None

    # Mise à jour de l'état
    if Cd.value() == 1:
        etat = "fourche"
    elif Dist < 12 and etat != "recherche_bleu":
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
        cmd_moteur(100, 10, 10)  # Reculer (av_ar=100)
        time.sleep_ms(500)
        arreter_moteurs()
        etat = "recherche_bleu"
    elif etat == "suivre" and Recherche_rouge:
        Recherche_rouge.sort(key=lambda b: b.pixels(), reverse=True)
        largest_blob = Recherche_rouge[-1]
        suivre_balle(largest_blob.cx(), largest_blob.cy(), img.width())
        LED_R.off()
        LED_V.on()
    elif etat == "recherche_bleu":
        Buzzr.low()
        chercher_sol_bleu(img)
        time.sleep_ms(500)
        LED_R.on()
        LED_V.off()
    elif etat == "recherche":
        chercher_balle()
        LED_R.on()
        LED_V.off()

    Buzzr.low()
    time.sleep_ms(50)
    print("FPS: {:.1f}, Etat: {}, Dist: {:.1f} cm, Code: {}".format(clock.fps(), etat, Dist, code))
