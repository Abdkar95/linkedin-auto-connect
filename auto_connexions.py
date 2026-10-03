"""
Automatisation écran : recherche -> filtre "Personnes" -> "Se connecter" -> "Envoyer sans note"
-> page "Suivant" -> ... jusqu'à blocage.

Fonctionne sur l'écran tel qu'il est (pas de navigateur piloté) :
- pyautogui  : clics, frappe, scroll, captures d'écran
- pytesseract: lecture du texte à l'écran pour trouver les boutons

ARRÊT D'URGENCE : envoie brutalement la souris dans un coin de l'écran.
"""

import os
import re
import shutil
import sys
import time

import pyautogui
import pytesseract
import numpy as np
from PIL import Image, ImageFilter, ImageOps

# --- Chemin de Tesseract (laisse None pour la détection automatique) ---
TESSERACT_CMD = None   # ex. r"D:\Outils\Tesseract-OCR\tesseract.exe"


def configurer_tesseract():
    """Trouve tesseract.exe (PATH ou emplacements Windows habituels) ou arrête proprement."""
    candidats = [
        TESSERACT_CMD,
        shutil.which("tesseract"),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
    ]
    for chemin in candidats:
        if chemin and os.path.isfile(chemin):
            pytesseract.pytesseract.tesseract_cmd = chemin
            langues = pytesseract.get_languages(config="")
            if "fra" not in langues:
                sys.exit("Tesseract trouvé mais sans le français (fra). "
                         "Réinstalle-le en cochant 'French' dans 'Additional language data'.")
            return chemin
    sys.exit("Tesseract introuvable. Installe-le (programme Windows, pas via pip) :\n"
             "  https://github.com/UB-Mannheim/tesseract/wiki\n"
             "ou renseigne TESSERACT_CMD en haut du script.")

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
SCROLL = 500                # amplitude d'un coup de molette (baisser si ça saute des profils)
# ====================================================================

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.3
MAC = sys.platform == "darwin"


def log(msg):
    print(time.strftime("[%H:%M:%S]"), msg, flush=True)


_derniere = {"img": None, "mots": []}   # dernière capture, pour le mode debug


# --- Prétraitements OCR -------------------------------------------------
# Les boutons LinkedIn sont mal lus sur une capture brute (texte bleu, texte
# blanc sur fond coloré). On essaie donc plusieurs "lectures" de la même capture.

def _masques(img):
    a = np.asarray(img.convert("RGB")).astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    bleu = (b > 150) & (r < 90) & (g > 60) & (g < 150)      # bleu LinkedIn #0A66C2
    vert = (g > 80) & (r < 60) & (b < 100) & (g > b)         # pastille de filtre active
    return bleu, vert


def _texte_sur_fond(masque):
    """Texte clair posé sur une zone colorée -> texte noir sur fond blanc."""
    zone = Image.fromarray((masque * 255).astype("uint8"))
    zone = zone.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.MinFilter(9))
    texte = (np.asarray(zone) > 0) & ~masque
    return Image.fromarray(np.where(texte, 0, 255).astype("uint8"))


def _versions(img):
    """Génère (nom, image, config tesseract) dans l'ordre du moins au plus coûteux."""
    yield "gris", ImageOps.grayscale(img), ""
    bleu, vert = _masques(img)
    yield "texte_bleu", Image.fromarray(np.where(bleu, 0, 255).astype("uint8")), "--psm 11"
    yield "fond_colore", _texte_sur_fond(bleu | vert), "--psm 11"


def _chercher_dans(d, cibles, f, limite_y):
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
        pos = ((x1 + x2) / 2 * f, (y1 + y2) / 2 * f)
        if limite_y and pos[1] > limite_y:
            continue
        return pos
    return None


def _norm(mot):
    mot = re.sub(r"[^\wàâçéèêëîïôûùüÿœ]", "", mot.lower())
    return {"ler": "1er"}.get(mot, mot)        # confusion OCR fréquente


def trouver(texte, haut_max=None):
    """Cherche `texte` (un ou plusieurs mots) à l'écran, en essayant plusieurs lectures.
    `haut_max` (0-1) : ne garder que les occurrences dans cette fraction haute de l'écran.
    Renvoie (x, y) du centre de la 1re occurrence (haut -> bas), ou None."""
    img = pyautogui.screenshot()
    _derniere["img"] = img
    largeur_ecran, hauteur_ecran = pyautogui.size()
    f = (largeur_ecran / img.width) / UPSCALE          # pixel OCR -> coordonnée écran
    limite_y = hauteur_ecran * haut_max if haut_max else None
    cibles = [_norm(m) for m in texte.split()]
    _derniere["mots"] = []

    for nom, version, config in _versions(img):
        version = version.resize((img.width * UPSCALE, img.height * UPSCALE))
        d = pytesseract.image_to_data(version, lang=LANG, config=config,
                                      output_type=pytesseract.Output.DICT)
        _derniere["mots"].append(f"[{nom}] " + " ".join(m for m in d["text"] if m.strip()))
        pos = _chercher_dans(d, cibles, f, limite_y)
        if pos:
            return pos
    return None


def attendre(texte, timeout=10, haut_max=None):
    """Comme trouver(), mais réessaie jusqu'à `timeout` secondes (page en chargement)."""
    fin = time.time() + timeout
    while True:
        pos = trouver(texte, haut_max)
        if pos or time.time() >= fin:
            return pos
        time.sleep(1)


def sauver_debug(nom):
    """Enregistre la dernière capture et les mots lus par l'OCR dans debug/."""
    os.makedirs("debug", exist_ok=True)
    horo = time.strftime("%H%M%S")
    if _derniere["img"] is not None:
        _derniere["img"].save(f"debug/{horo}_{nom}.png")
    with open(f"debug/{horo}_{nom}.txt", "w", encoding="utf-8") as fic:
        fic.write("\n\n".join(_derniere["mots"]))
    log(f"Debug enregistré : debug/{horo}_{nom}.png (+ .txt des mots lus)")


def cliquer(texte, pause=PAUSE, timeout=0, haut_max=None):
    pos = attendre(texte, timeout, haut_max) if timeout else trouver(texte, haut_max)
    if pos:
        pyautogui.click(*pos)
        time.sleep(pause)
        return True
    return False


def empreinte_ecran():
    """Empreinte légère de la zone centrale (hors barre des tâches et horloge)."""
    img = pyautogui.screenshot()
    l, h = img.size
    return img.crop((0, int(h * 0.15), int(l * 0.75), int(h * 0.85))).resize((160, 90)).tobytes()


def placer_souris_contenu():
    """La molette agit sous la souris : on la met au milieu de la liste de résultats."""
    l, h = pyautogui.size()
    pyautogui.moveTo(l * 0.35, h * 0.6)


def scroller_bas():
    """Scrolle vers le bas. Renvoie False si l'écran n'a pas bougé deux fois de suite
    (fin de page ; la 2e tentative laisse le temps au chargement différé)."""
    placer_souris_contenu()
    for _ in range(2):
        avant = empreinte_ecran()
        pyautogui.scroll(-SCROLL)
        time.sleep(1.2)
        if empreinte_ecran() != avant:
            return True
    return False


def traiter_page(compteur):
    """Envoie les invitations visibles sur la page en scrollant jusqu'en bas.
    Renvoie (compteur, stop)."""
    echecs = 0
    while True:
        if compteur >= MAX_INVITATIONS:
            log(f"Plafond de {MAX_INVITATIONS} invitations atteint.")
            return compteur, True

        if cliquer("Se connecter"):
            if cliquer("Envoyer sans note", timeout=5):
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
    log(f"Tesseract : {configurer_tesseract()}")
    log(f"Bascule sur la fenêtre LinkedIn (Alt+Tab) et place ta souris sur la barre "
        f"de recherche. Démarrage dans {DELAI_CALIBRAGE} s...")
    for s in range(DELAI_CALIBRAGE, 0, -1):
        print(f"  {s}...", flush=True)
        time.sleep(1)

    # 1. Localisation de la barre de recherche : OCR d'abord, souris en secours
    champ = trouver("Rechercher", haut_max=0.2)
    if champ:
        log(f"Barre 'Rechercher' détectée automatiquement : ({champ[0]:.0f}, {champ[1]:.0f})")
    else:
        champ = pyautogui.position()
        log(f"Barre non détectée, position de la souris utilisée : {champ}")

    # 2. Saisie de la recherche
    pyautogui.click(*champ)
    time.sleep(0.5)
    pyautogui.hotkey("command" if MAC else "ctrl", "a")
    pyautogui.write(RECHERCHE, interval=0.05)
    pyautogui.press("enter")

    # 3. Filtre "Personnes"
    #    Si on est déjà sur les résultats Personnes (filtres "Recrutement actif", "1er"...),
    #    on ne reclique pas : cela ouvrirait le menu déroulant de la pastille.
    time.sleep(PAUSE_PAGE)
    if attendre("Recrutement actif", timeout=5, haut_max=0.35):
        log("Déjà sur les résultats 'Personnes'.")
    elif cliquer("Personnes", pause=PAUSE_PAGE, timeout=15, haut_max=0.35):
        log("Filtre 'Personnes' activé.")
    else:
        log("Élément 'Personnes' introuvable -> arrêt.")
        sauver_debug("personnes_introuvable")
        return

    # 4. Boucle sur les pages
    compteur = 0
    for page in range(1, MAX_PAGES + 1):
        log(f"--- Page {page} ---")
        compteur, stop = traiter_page(compteur)
        if stop:
            break
        if not cliquer("Suivant", pause=PAUSE_PAGE, timeout=5):
            log("Bouton 'Suivant' introuvable -> bloqué, arrêt.")
            sauver_debug("suivant_introuvable")
            break
    else:
        log(f"Plafond de {MAX_PAGES} pages atteint.")

    log(f"Terminé : {compteur} invitation(s) envoyée(s).")


if __name__ == "__main__":
    try:
        main()
    except pyautogui.FailSafeException:
        log("Arrêt d'urgence (souris dans un coin).")