# Changelog

Toutes les évolutions notables du projet sont consignées ici.
Format inspiré de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/).

## [Non publié]

### Ajouté
- Détection automatique de Tesseract sous Windows et vérification du pack français
- Détection automatique de la barre « Rechercher » par OCR (souris en secours)
- Attente active des éléments pendant le chargement des pages (`attendre()`)
- Mode debug : capture + mots lus enregistrés dans `debug/` en cas de blocage
- Lecture OCR en plusieurs passes : capture brute, texte bleu isolé, texte blanc sur fond coloré
- Paramètre `SCROLL` (amplitude de la molette)

### Modifié
- Message d'erreur explicite si Tesseract est absent
- `.gitignore` : exclusion des environnements virtuels `.virtuel/`

### Corrigé
- Recherche tapée hors de LinkedIn quand le terminal masquait la page
- Faux positifs de « Personnes » limités à la partie haute de l'écran
- Boutons « Se connecter » (texte bleu) et « Personnes » (blanc sur vert) non détectés
- Le défilement ne se faisait pas : souris replacée sur la liste avant chaque coup de molette, fin de page confirmée par 2 essais
- Plus de clic sur « Personnes » quand on est déjà sur ces résultats (ouvrait le menu déroulant)

## [0.1.0] - 2026-10-03

### Ajouté
- Première version du script `auto_connexions.py`
- Calibrage de la barre de recherche par position de la souris
- Saisie du mot-clé et clic sur le filtre « Personnes »
- Détection OCR des boutons « Se connecter », « Envoyer sans note » et « Suivant »
- Scroll automatique et détection de fin de page
- Plafonds (invitations, pages, échecs) et arrêt d'urgence
- Gestion des écrans Retina / mise à l'échelle