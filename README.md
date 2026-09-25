# Plugin QGIS Cycling Facilities

Stage de fin d'études Geodata Paris à la DDT47.
Implémentation d’un plugin QGIS permettant de localiser des sites pertinents pour l'implantation de hubs de mobilité.

## Installer le plugin sur QGIS

Le dossier contenant le plugin est le dossier plugin.
Afin de faire fonctionner le plugin, il est nécessaire d'exporter le repository en zip.

Ce dossier .zip peut ensuite êre ajouté dans QGIS. Pour cela, il faut le charger depuis "Extensions / Installer/gérer les extensions / installer depuis un zip".
Une fois le plugin chargé, installer l'extension Plugin Reloader et sélectionner le plugin cycling\_facilities dans les paramètres de l'extension.
Une nouvelle icône apparaît, qui permet de lancer le plugin.

## Utilisation

Pour le bon fonctionnement du plugin, il faut fournir les données suivantes :

1. **Couche réseau de route :**
Un fichier du réseau contenant des géométries de type linéaire. Par exemple, un réseau issu de la BDTOPO convient parfaitement.
2. **Couche population :**
Un fichier de population contenant des géométries de type polygonale.
3. **Données points d'intérêt** 
Un fichier de points d'intérêt avec une géométrie ponctuelle par exemple la BPE de l'INSEE
4. **Données d'accidentologie**
Un fichier de localisation des accidents sous forme de points.

Ces fichiers doivent dépendre du même système de projection.

