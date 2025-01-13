# Jeu Quiz avec Thèmes Variés et Mode Duel en Ligne

## Description du projet
Ce projet a été réalisé dans le cadre de la SAÉ32, une activité pédagogique visant à concevoir un jeu de quiz interactif. Le jeu permet aux utilisateurs de s'inscrire, de se connecter et de participer à des quiz sur différents thèmes. Il inclut également un mode duel en ligne pour permettre à deux joueurs de s'affronter.

## Fonctionnalités principales
- Interface utilisateur interactive pour s'inscrire, se connecter et choisir des thèmes.
- Mode duel permettant des parties en ligne.
- Gestion des utilisateurs, des thèmes, des questions et des scores.
- Stockage des données dans une base SQLite.

## Langages et technologies utilisés
- **Python** : Langage principal pour la logique du jeu, le serveur et l'interface utilisateur (Tkinter).
- **HTML** : Utilisé pour des aspects secondaires de présentation ou d'export.

## Prérequis
Pour exécuter ce projet, vous devez avoir installé :
- **Python 3** : Assurez-vous que Python 3 est installé sur votre système.

## Installation
1. Clonez ce dépôt sur votre machine locale :
2. Accédez au répertoire du projet :
3. Installez les dépendances (si nécessaire) :

## Détails des fichiers
Voici un résumé des principaux fichiers du projet :

1. **`quiz_client.py`** : Ce fichier gère l'interface utilisateur et la connexion client-serveur. Il utilise Tkinter pour afficher un jeu de quiz interactif, permettant aux utilisateurs de s'inscrire, se connecter, et participer à des quiz sur divers thèmes.

2. **`quiz_database.py`** : Ce fichier contient les opérations sur la base de données SQLite pour gérer les utilisateurs, les thèmes, les questions, et les scores. Il inclut la création des tables, la vérification des utilisateurs, l'ajout de questions, et la récupération des scores et thèmes.

3. **`quiz_serveur.py`** : Ce fichier implémente le serveur qui traite les connexions des clients, les commandes liées au quiz, et la logique de gestion des parties. Il interagit avec la base de données pour valider les utilisateurs, gérer les jeux, et enregistrer les scores.

## Collaboration
Nous avons collaboré à quatre sur ce projet, en utilisant Trello pour planifier et suivre l'état d'avancement des tâches. Cette organisation a facilité la répartition du travail et a permis une gestion efficace du projet.
https://trello.com/b/ZMWzRrzC/quizz-sae32

## Utilisation
Pour lancer le jeu su rl'interpréteur python :
1. Exécutez d'abord le serveur :
```bash
python quiz_serveur.py
```
2. Ensuite, lancez le client :
```bash
python quiz_client.py
```
3. Suivez les instructions à l'écran pour vous connecter, choisir un thème et commencer à jouer.

On peut aussi tout simplement accéder à la page web avec le lien suivant : 

## Contributions
Les contributions sont les bienvenues ! Si vous souhaitez améliorer ce projet, vous pouvez :
- Soumettre un pull request.
- Signaler des problèmes dans l'onglet [Issues](https://github.com/votre-repo/quiz-jeu/issues).

## Licence
Ce projet est sous licence MIT. Veuillez consulter le fichier `LICENSE` pour plus d'informations.

## Remerciements
Nous remercions notre équipe projet pour son implication ainsi que notre encadrant pour son accompagnement tout au long de cette SAÉ32.

---
Merci de votre intérêt pour ce projet ! Si vous avez des questions, n'hésitez pas à nous contacter.

