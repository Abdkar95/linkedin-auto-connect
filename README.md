# LinkedIn Auto-Connect (automatisation écran)

Script Python qui automatise l'envoi d'invitations LinkedIn **en pilotant directement l'écran** (souris + clavier), sans navigateur piloté ni API. Les boutons sont repérés par reconnaissance de texte (OCR).

> ⚠️ **Avertissement** — Les conditions d'utilisation de LinkedIn interdisent l'automatisation, et la plateforme limite les invitations (environ 100 par semaine). Un usage intensif peut entraîner une restriction du compte. Projet à visée d'apprentissage : utilise-le avec des volumes modestes et à tes risques.

## Fonctionnement

```
Barre de recherche ──► saisie du mot-clé ──► clic "Personnes"
        │
        ▼
 ┌─► "Se connecter" visible ? ── oui ──► clic ──► "Envoyer sans note"
 │          │ non
 │          ▼
 │   scroll vers le bas ── fin de page ? ── non ──┐
 │          │ oui                                  │
 │          ▼                                      │
 └── clic "Suivant" ◄──────────────────────────────┘
            │ introuvable / bloqué
            ▼
          ARRÊT
```

1. Compte à rebours : place ta souris sur la barre de recherche, sa position est mémorisée. 
2. Le script saisit le mot-clé (`RECHERCHE`) et valide.
3. Il clique sur le filtre **Personnes**.
4. Sur chaque page : clic sur **Se connecter** puis **Envoyer sans note**, jusqu'à ce qu'il n'y en ait plus (en scrollant).
5. Passage à la page **Suivant** et même scénario.
6. Arrêt si un élément est introuvable, si un plafond est atteint ou après trop d'échecs consécutifs.

## Prérequis

- Python 3.9+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) avec le pack de langue **français**
  - **Windows** : installeur [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki) (cocher *French*), puis renseigner le chemin dans le script (`tesseract_cmd`)
  - **macOS** : `brew install tesseract tesseract-lang`
  - **Linux** : `sudo apt install tesseract-ocr tesseract-ocr-fra`
- macOS : autoriser le terminal dans *Réglages > Confidentialité et sécurité > Accessibilité* et *Enregistrement de l'écran*

## Installation

```bash
git clone https://github.com/abdkar95/linkedin-auto-connect.git
cd linkedin-auto-connect
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements.txt
```

## Utilisation

1. Ouvre LinkedIn dans ton navigateur (connecté).
2. Lance :
   ```bash
   python auto_connexions.py
   ```
3. Pendant le compte à rebours, place la souris sur la barre de recherche.
4. Laisse tourner sans toucher la souris.

**Arrêt d'urgence** : envoie la souris dans un coin de l'écran (failsafe `pyautogui`).

## Configuration

Paramètres en haut de `auto_connexions.py` :

| Paramètre | Défaut | Rôle |
|---|---|---|
| `RECHERCHE` | `"head data"` | Mot-clé saisi dans la barre de recherche |
| `MAX_INVITATIONS` | `20` | Plafond d'invitations par exécution |
| `MAX_PAGES` | `10` | Plafond de pages parcourues |
| `MAX_ECHECS` | `3` | Échecs consécutifs avant arrêt |
| `PAUSE` | `1.5` | Attente après chaque clic (s) |
| `PAUSE_PAGE` | `3.0` | Attente après chargement d'une page (s) |
| `DELAI_CALIBRAGE` | `5` | Temps pour placer la souris (s) |
| `LANG` | `"fra+eng"` | Langues OCR |
| `UPSCALE` | `2` | Agrandissement de la capture pour l'OCR |

## Dépannage

| Problème | Piste |
|---|---|
| Un bouton n'est pas détecté | Monter `UPSCALE` à 3, ou zoomer le navigateur à 110–125 % |
| Clic décalé | Vérifier la mise à l'échelle Windows ; le script gère Retina |
| `TesseractNotFoundError` | Installer Tesseract ou renseigner `tesseract_cmd` |
| Popup sans « Envoyer sans note » | Normal (email demandé…) : fermée avec Échap, le script continue |

## Stack

- [`pyautogui`](https://pyautogui.readthedocs.io/) — contrôle souris/clavier et captures d'écran
- [`pytesseract`](https://github.com/madmaze/pytesseract) — OCR pour localiser les boutons
- [`Pillow`](https://python-pillow.org/) — traitement d'image

## Feuille de route

- [ ] Paramètres en ligne de commande (`--recherche`, `--max`…)
- [ ] Journal des invitations envoyées (CSV)
- [ ] Délais aléatoires entre les actions
- [ ] Mode « simulation » (détection sans clic)
- [ ] Tests unitaires de la fonction `trouver()`

Voir [CHANGELOG.md](CHANGELOG.md) pour l'historique des versions.

## Auteur

**Abdoul-Karym Traoré** — [LinkedIn](https://linkedin.com/in/traoreabdoul) · [GitHub](https://github.com/abdkar95)
