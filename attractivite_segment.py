# -*- coding: utf-8 -*-
"""
Created on Tue Aug 25 17:07:48 2026

@author: eleonore.lagourgue
"""
from qgis.PyQt.QtCore import QCoreApplication, QVariant

from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterNumber,
    QgsProcessingParameterFeatureSink,
    QgsProcessingUtils,
    QgsFeature,
    QgsGeometry,
    QgsPointXY
)
from qgis import processing

class TripGenerationProcessor(QgsProcessingAlgorithm):
    ROADS = 'ROADS'
    POIS = 'POIS'
    POPULATION = 'POPULATION'
    OUTPUT = 'OUTPUT'
    def name(self):
        return 'Génération de Trafic (Services & Population)'

    

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr(self.name())

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr(self.groupId())

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'Traitements'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return TripGenerationProcessor()
    def initAlgorithm(self, config=None):
        # Couche du réseau routier (lignes)
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.ROADS, 'Réseau routier', [QgsProcessing.TypeVectorLine]
            )
        )
        # Points d'intérêt / Générateurs de trafic (points)
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.POIS, 'Points Générateurs de Trafic (PNT)', [QgsProcessing.TypeVectorPoint]
            )
        )
        # Couche de population (carroyage ou polygones)
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.POPULATION, 'Densité de Population', [QgsProcessing.TypeVectorPolygon]
            )
        )
        # Sink de sortie
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT, 'Réseau enrichi de la demande'
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        roads = self.parameterAsVectorLayer(parameters, self.ROADS, context)
        pois = self.parameterAsVectorLayer(parameters, self.POIS, context)
        pop = self.parameterAsVectorLayer(parameters, self.POPULATION, context)

        #1. Densité de Kernel (KDE) pour la génération de trafic PNT
        feedback.pushInfo("Calcul de la densité des PNT...")
        kde_result = processing.run("qgis:heatmapkerneldensityestimation", {
            'INPUT': pois,
            'RADIUS': 1000, # Rayon de 1 km d'attractivité
            'PIXEL_SIZE': 10,
            'WEIGHT_FIELD': 'poids', # Poids selon le type de POI (ex: gare=3, commerce=1)
            'OUTPUT': QgsProcessingUtils.generateTempFilename('kde_pois.tif')
        }, context=context, feedback=feedback)

        #2. Statistiques de zone sur les segments routiers (Attribution du score PNT)
        feedback.pushInfo("Attribution des scores d'attractivité aux tronçons...")
        roads_with_pois = processing.run("native:zonalstatisticsgroupbyvariable", {
            'INPUT_RASTER': kde_result['OUTPUT'],
            'RASTER_BAND': 1,
            'INPUT_VECTOR': roads,
            'COLUMN_PREFIX': 'poi_score_',
            'STATISTICS': [2], # Moyenne (Mean)
            'OUTPUT': QgsProcessingUtils.generateTempFilename('roads_pois.gpkg')
        }, context=context, feedback=feedback)

        #3. Jointure spatiale avec la population (Somme de pop dans un buffer autour des tronçons)
        feedback.pushInfo("Prise en compte de la population riveraine...")
        roads_buffered = processing.run("native:buffer", {
            'INPUT': roads_with_pois['OUTPUT'],
            'DISTANCE': 200, # Tampon de 200m
            'OUTPUT': QgsProcessingUtils.generateTempFilename('roads_buf.gpkg')
        }, context=context, feedback=feedback)

        pop_joined = processing.run("native:joinattributesbylocation", {
            'INPUT': roads_buffered['OUTPUT'],
            'JOIN': pop,
            'PREDICATE': [0], # Intersecte
            'JOIN_FIELDS': ['pop_count'],
            'METHOD': 0,
            'DISCARD_NON_MATCHING': False,
            'PREFIX': 'pop_',
            'OUTPUT': parameters[self.OUTPUT]
        }, context=context, feedback=feedback)

        return {self.OUTPUT: pop_joined['OUTPUT']}

    