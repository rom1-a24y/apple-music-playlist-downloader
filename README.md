# Apple Music Playlist Downloader

Télécharge toutes les musiques d'une playlist Apple Music publique en MP3, numérotées dans l'ordre — idéal pour les transférer sur une montre Coros ou tout lecteur MP3.

## Prérequis

- **Windows 10 / 11**
- **Python 3.10+** — [python.org](https://www.python.org/downloads/)
  _(lors de l'installation, cocher "Add Python to PATH")_

## Installation (une seule fois)

1. Télécharge ou clone ce dépôt
2. Ouvre un terminal dans le dossier du projet
3. Double-clique sur **`install.bat`**

Le script installe automatiquement :
- ffmpeg (via winget)
- les dépendances Python (Flask, yt-dlp, Playwright…)
- le navigateur Chromium headless

## Utilisation

1. Double-clique sur **`start.bat`**
2. Ouvre **http://localhost:5000** dans ton navigateur
3. Colle le lien de ta playlist Apple Music publique
4. Clique **Télécharger**

Les fichiers MP3 sont créés dans le dossier `downloads/<nom de la playlist>/`, nommés :
```
01 - Titre - Artiste.mp3
02 - Titre - Artiste.mp3
...
```

## Notes

- La playlist Apple Music doit être **publique** (partageable via lien)
- Le téléchargement d'une playlist de ~80 titres prend environ 15-20 minutes
- Les fichiers sont téléchargés depuis YouTube via une recherche automatique (titre + artiste)
