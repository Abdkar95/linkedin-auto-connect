"""
Automatisation écran : recherche -> filtre "Personnes" -> "Se connecter" -> "Envoyer sans note"
-> page "Suivant" -> ... jusqu'à blocage.

Fonctionne sur l'écran tel qu'il est (pas de navigateur piloté) :
- pyautogui  : clics, frappe, scroll, captures d'écran
- pytesseract: lecture du texte à l'écran pour trouver les boutons

ARRÊT D'URGENCE : envoie brutalement la souris dans un coin de l'écran.
"""

import re
import sys
import time

import pyautogui
import pytesseract
from PIL import ImageOps

# --- Windows : décommente et adapte si Tesseract n'est pas dans le PATH ---
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ============================ PARAMÈTRES ============================
RECHERCHE = "head data"     # texte à saisir
MAX_INVITATIONS = 20        # plafond d'invitations par exécution
MAX_PAGES = 10              # plafond de pages "Suivant"
MAX_ECHECS = 3              # échecs consécutifs avant arrêt
PAUSE = 1.5                 # attente après chaque clic (s)
PAUSE_PAGE = 3.0            # attente après chargement d'une page (s)
DELAI_CALIBRAGE = 5         # secondes pour placer la souris sur le champ
LANG = "fra+eng"            # langues OCR
UPSCALE = 2                 # agrandissement de la capture -> meilleur OCR
# ====================================================================

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.5
MAC = sys.platform == "darwin"


def log(msg):
    print(time.strftime("[%H:%M:%S]"), msg, flush=True)


def capture():
    """Capture l'écran, renvoie (image prête pour l'OCR, facteur pixel -> coordonnée écran)."""
    img = pyautogui.screenshot()
    largeur_ecran, _ = pyautogui.size()
    ratio = largeur_ecran / img.width          # gère les écrans Retina / mise à l'échelle
    gris = ImageOps.grayscale(img)
    gris = gris.resize((gris.width * UPSCALE, gris.height * UPSCALE))
    return gris, ratio / UPSCALE


def _norm(mot):
    return re.sub(r"[^\wàâçéèêëîïôûùüÿœ]", "", mot.lower())


def trouver(texte):
    """Cherche `texte` (un ou plusieurs mots) à l'écran.
    Renvoie (x, y) du centre de la 1re occurrence (haut -> bas), ou None."""
    img, f = capture()
    d = pytesseract.image_to_data(img, lang=LANG, output_type=pytesseract.Output.DICT)
    cibles = [_norm(m) for m in texte.split()]
    mots = [_norm(m) for m in d["text"]]
    n = len(cibles)

    for i in range(len(mots) - n + 1):
        if mots[i:i + n] != cibles:
            continue
        # tous les mots doivent être sur la même ligne
        cle = (d["block_num"][i], d["par_num"][i], d["line_num"][i])
        if any((d["block_num"][i + k], d["par_num"][i + k], d["line_num"][i + k]) != cle
               for k in range(n)):
            continue
        x1 = d["left"][i]
        x2 = d["left"][i + n - 1] + d["width"][i + n - 1]
        y1 = min(d["top"][i + k] for k in range(n))
        y2 = max(d["top"][i + k] + d["height"][i + k] for k in range(n))
        return ((x1 + x2) / 2 * f, (y1 + y2) / 2 * f)
    return None


def cliquer(texte, pause=PAUSE):
    pos = trouver(texte)
    if pos:
        pyautogui.click(*pos)
        time.sleep(pause)
        return True
    return False


def empreinte_ecran():
    """Empreinte légère de l'écran, pour savoir si un scroll a changé quelque chose."""
    return pyautogui.screenshot().resize((160, 90)).tobytes()


def scroller_bas():
    """Scrolle vers le bas. Renvoie False si l'écran n'a pas bougé (fin de page)."""
    avant = empreinte_ecran()
    pyautogui.scroll(-500)
    time.sleep(1)
    return empreinte_ecran() != avant


def traiter_page(compteur):
    """Envoie les invitations visibles sur la page en scrollant jusqu'en bas.
    Renvoie (compteur, stop)."""
    echecs = 0
    while True:
        if compteur >= MAX_INVITATIONS:
            log(f"Plafond de {MAX_INVITATIONS} invitations atteint.")
            return compteur, True

        if cliquer("Se connecter"):
            if cliquer("Envoyer sans note"):
                compteur += 1
                echecs = 0
                log(f"Invitation envoyée ({compteur}).")
            else:
                # popup inattendue (email demandé, "comment connaissez-vous..." etc.)
                echecs += 1
                log("Popup sans 'Envoyer sans note' -> fermeture (Échap).")
                pyautogui.press("esc")
                time.sleep(PAUSE)
                if echecs >= MAX_ECHECS:
                    log("Trop d'échecs consécutifs, je m'arrête.")
                    return compteur, True
            continue

        # plus de "Se connecter" visible : on descend
        if not scroller_bas():
            return compteur, False   # bas de page atteint


def main():
    log(f"Place ta souris sur la barre de recherche. Démarrage dans {DELAI_CALIBRAGE} s...")
    for s in range(DELAI_CALIBRAGE, 0, -1):
        print(f"  {s}...", flush=True)
        time.sleep(1)
    champ = pyautogui.position()
    log(f"Position du champ mémorisée : {champ}")

    # 1. Saisie de la recherche
    pyautogui.click(champ)
    time.sleep(0.5)
    pyautogui.hotkey("command" if MAC else "ctrl", "a")
    pyautogui.write(RECHERCHE, interval=0.05)
    pyautogui.press("enter")
    time.sleep(PAUSE_PAGE)

    # 2. Filtre "Personnes"
    if not cliquer("Personnes", pause=PAUSE_PAGE):
        log("Élément 'Personnes' introuvable -> arrêt.")
        return

    # 3. Boucle sur les pages
    compteur = 0
    for page in range(1, MAX_PAGES + 1):
        log(f"--- Page {page} ---")
        compteur, stop = traiter_page(compteur)
        if stop:
            break
        if not cliquer("Suivant", pause=PAUSE_PAGE):
            log("Bouton 'Suivant' introuvable -> bloqué, arrêt.")
            break
    else:
        log(f"Plafond de {MAX_PAGES} pages atteint.")

    log(f"Terminé : {compteur} invitation(s) envoyée(s).")


if __name__ == "__main__":
    try:
        main()
    except pyautogui.FailSafeException:
        log("Arrêt d'urgence (souris dans un coin).")
