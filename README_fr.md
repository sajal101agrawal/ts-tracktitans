# TS2 - Train Signalling Simulation
version 0.7

## Pr�sentation
**Train Signalling Simulation (TS2)** est un jeu de simulation ferroviaire o� vous
devez aiguiller les trains sur une zone et les garder � l'heure.

## Liens
* Site de TS2 - [ts2.github.io](http://ts2.github.io/)
* Chat TS2 (en anglais) - [irc.freenode.net#trainsigsim](irc://irc.freenode.net#trainsigsim)
* Page du projet TS2 sur Github - [github.com/ts2](http://github.com/ts2/)

## Statut
TS2 est un logiciel beta ce qui signifie qu'il est jouable, mais qu'il lui manque
encore de nombreuses fonctionnalit�s que l'on peut attendre d'une simulation.
Au d�marrage de TS2, vous pourrez t�l�charger des simulations depuis notre serveur [ts2-data](https://github.com/ts2/ts2-data)

De nouvelles simulations peuvent �tre cr��es gr�ce � l'�diteur incorpor� dans
le logiciel.

## Installation
* Versions officielles:
    - Windows 64 bits: installer � partir de l'installateur et lancer ts2.exe.
    - Autres plateformes: voir installation depuis les sources.
* Installation � partir des sources:
    - T�l�charger et installer Python v3 ou sup�rieur depuis [www.python.org](http://www.python.org).
    - T�l�charger et installer PyQt v5 ou sup�rieur depuis [http://www.riverbankcomputing.co.uk](http://www.riverbankcomputing.co.uk).
    - R�cuperer les sources depuis [GitHub](https://github.com/ts2/ts2/releases/tag/v0.7.0).
    - Lancer start-ts2.py.
* Post installation:
    - T�l�charger le serveur de simulation en ouvrant le menu "Fichier->Options" et cliquer sur "T�l�charger le serveur".

## Jeu (Guide rapide)
* Charger une simulation depuis le dossier _simulation_ (ou le dossier _data_ si vous avez install� depuis les sources).
    Si vous voulez charger une simulation d'une version pr�c�dente de TS2, vous devez d'abord l'ouvrir avec l'�diteur
    puis la sauvegarder avant de la charger � nouveau dans la fen�tre principale.
* Activation des routes:
    - Pour faire passer un signal du rouge au vert, vous devez activer une route de ce signal vers le suivant.
    - Pour activer une route, cliquer sur un signal puis sur le suivant. S'il est possible d'activer une route
        entre ces deux signaux, la voie entre les deux signaux s'affiche en blanc, les aiguilles sont orient�es
        automatiquement selon cette route et le signal d'entr�e passe au jaune (ou au vert si le second signal
        est d�j� jaune ou vert).
    - Pour annuler une route, cliquer avec le bouton droit sur le premier signal.
    - Les routes sont d�truites automatiquement au passage du premier train. Cependant, vous pouvez activer une
        route de fa�on persistente en maintenant la touche MAJ enfonc�e lorsque vous cliquez sur le deuxi�me
        signal. Les routes persistentes sont rep�r�es par un petit carr� blanc � c�t� de leur signal d'entr�e.
    - Activation forc�e: Il est possible de forcer l'activation d'une route en appuyant simultan�ment sur _ctrl_
        et _alt_ lorsque vous cliquez sur le second signal. Attention, cela va activer la route sans v�rifier
        qu'il n'y a pas d'autres routes en conflit et peut engendrer des accidents de train ou d'autres effets
        non d�sir�s.
* Donn�es des trains:
    - Cliquer sur le code d'un train sur la carte ou dans la liste des trains pour voir ses donn�es dans la
        fen�tre "D�tails du train". La fen�tre "D�tails de la mission" se mettra � jour �galement.
* Donn�es des gares:
    - Cliquer sur un quai sur la carte pour afficher les horaires de la gare dans la fen�tre "Gare".
* Interagir avec les trains:
    - Cliquer avec le bouton droit sur le code d'un train sur la carte ou dans la liste des trains ou dans la
        fen�tre "D�tails du train" pour afficher le menu relatif au train. Ce menu permet de:
        + Assigner une nouvelle mission au train. S�lectionner la mission dans la fen�tre qui apparait et cliquer
        sur "Ok".
        + Recommencer la mission, c'est-�-dire de signifier au machiniste de s'arr�ter � nouveau � la premi�re
        gare.
        + Inverser le sens de marche du train.
    - Les trains changent automatiquement de mission lorsque la mission actuelle est termin�e.
* Vous devriez voir les trains rouler, s'arr�ter aux signaux ferm�s et aux gares pr�vues dans leur mission. Ils
    doivent quitter les gares � l'horaire pr�vu ou pass� un temps donn� apr�s leur arriv�e si l'horaire de d�part
    pr�vu est d�j� pass�.
* Score:
    A chaque fois qu'un train arrive en retard � une gare, s'arr�te sur le mauvais quai ou est aiguill� dans une
    mauvaise direction, des points de p�nalit� sont ajout�s au score.

## D�veloppement

Que vous souhaitiez �crire votre propre simulation avec l'�diteur ou d�velopper un nouveau client pour interagir avec TS2,
allez voir notre 
[Manuel technique](https://github.com/ts2/ts2-sim-server/blob/master/docs/ts2-technical-manual.pdf)
(en anglais)

## Historique des versions

### Version 0.7:
- Nouvelle architecture client-serveur:
    - Mode multijoueur en connectant plusieurs joueurs sur la m�me simulation
    - API Websocket pour interagir avec la simulation

### Version 0.6:
- Nouvelle version Python3 / PyQt5
- D�placement du projet sur GitHub
- Nouveau site
- Les simulations sont maintenant au format JSON 
- Possibilit� de t�l�charger des simulations / signaux depuis ts2-data
- Marches � vue
- Division de train
- Nouveaux signaux param�triques
- Signaux BAL fran�ais
- Signaux de manoeuvre UK
- Am�lioration de l'interface
- Meilleure gestion des erreurs

### Version 0.5:
- Derni�re version PyQt4
- Editeur am�lior� incluant les caract�ristiques suivantes: 
    - S�lections multiples
    - Copier/Coller
    - Edition de propri�t�s en masse
    - Redimensionnement des quais avec la souris
- Nouveaux signaux avec :
    - Longueur r�duite
    - Code train positionable 
    - Nouveaux types de signaux (UK 4 aspects notamment)
