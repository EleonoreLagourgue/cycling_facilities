# -*- coding: utf-8 -*-
"""
Created on Fri Jul 17 16:37:12 2026

@author: eleonore.lagourgue
"""
from qgis.core import (
    QgsVectorLayer,
    QgsFeature, QgsGeometry, QgsFields, QgsField,
    QgsWkbTypes, QgsFeatureSink,
    QgsVectorFileWriter, QgsProject,
)
from qgis.PyQt.QtCore import QVariant

import json



import pandas as pd
import geopandas as gpd
from shapely import wkt as shapely_wkt
import pyogrio
import os
import tempfile
import pyarrow as pa
#%%

	
def gdf_from_layer_arrow(layer):
    # SDSL2025 version
    with tempfile.TemporaryDirectory() as tmpdirname:
        path = os.path.join(tmpdirname, "data.arrow")
 
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile 
        options.layerName = 'data'
        options.driverName = "arrow"
        options.layerOptions = ['GEOMETRY_ENCODING=GEOARROW']  # tentative
         
       
        result = QgsVectorFileWriter.writeAsVectorFormatV3(
        layer, path, QgsProject.instance().transformContext(), options
    )
        if result[0] != QgsVectorFileWriter.NoError:
            raise RuntimeError(f"Écriture échouée : {result}")
        print(os.path.getsize(path))
        try:
            with pa.memory_map(path, 'r') as source:
                table = pa.ipc.open_file(source).read_all()
        except pa.lib.ArrowInvalid:
            # au cas où ce serait plutôt du format "stream"
            with pa.memory_map(path, 'r') as source:
                table = pa.ipc.open_stream(source).read_all()

        gdf = gpd.GeoDataFrame.from_arrow(table)
        if gdf.crs is None:
            gdf = gdf.set_crs(layer.crs().authid(), allow_override=True)
    return gdf

def layer_to_gdf(layer):
    crs = layer.crs().authid()
    df = pd.DataFrame([feat.attributes() for feat in layer.getFeatures()],
                  columns=[field.name() for field in layer.fields()])
    df["geometry"] = df["geometry"].apply(lambda k: shapely_wkt.loads(k.asWkt()))
    
    gdf = gpd.GeoDataFrame(df, geometry="geometry", crs=crs)
    gdf = gdf.explode(index_parts=False).reset_index(drop=True)
    return gdf

    
    
def qgis_layer_to_gdf(layer: QgsVectorLayer) -> gpd.GeoDataFrame:
    """Convertit une QgsVectorLayer en GeoDataFrame."""
    # df = pd.DataFrame([feat.attributes() for feat in layer.getFeatures()],
    #               columns=[field.name() for field in layer.fields()])
    if layer is None or not layer.isValid():
        raise ValueError("Couche QGIS invalide ou introuvable.")

    crs = layer.crs().authid()  # ex: 'EPSG:2154'
    fields = [f.name() for f in layer.fields()]
    records = []
    
    
    df = pd.DataFrame([feat.attributes() for feat in layer.getFeatures()],
                  columns=[field.name() for field in layer.fields()])
    df["geometry"] = df["geometry"]
    for feature in layer.getFeatures():
        geom = feature.geometry()
        if geom is None or geom.isEmpty():
            continue

        attrs = {f: feature[f] for f in fields}
        attrs["geometry"] = shapely_wkt.loads(geom.asWkt())
        records.append(attrs)

    gdf = gpd.GeoDataFrame(records, geometry="geometry", crs=crs)

    #On explose les géométries multiples
    gdf = gdf.explode(index_parts=False).reset_index(drop=True)

    return gdf

def gdf_geom_to_qgs_wkbtype(gdf):
    """Déduit le type de géométrie QGIS à partir du GeoDataFrame."""
    geom_type = gdf.geom_type.iloc[0]  # ex: 'LineString', 'Point', 'Polygon'
    mapping = {
        "Point": QgsWkbTypes.Point,
        "LineString": QgsWkbTypes.LineString,
        "Polygon": QgsWkbTypes.Polygon,
        "MultiPoint": QgsWkbTypes.MultiPoint,
        "MultiLineString": QgsWkbTypes.MultiLineString,
        "MultiPolygon": QgsWkbTypes.MultiPolygon,
    }
    return mapping.get(geom_type, QgsWkbTypes.Unknown)


def gdf_to_qgsfields(gdf):
    """Construit un QgsFields à partir des colonnes non-géométrie du gdf."""
    fields = QgsFields()
    dtype_mapping = {
        "int64": QVariant.LongLong,
        "int32": QVariant.Int,
        "float64": QVariant.Double,
        "float32": QVariant.Double,
        "bool": QVariant.Bool,
        "object": QVariant.String,
        "datetime64[ns]": QVariant.DateTime,
    }
    for col in gdf.columns:
        if col == gdf.geometry.name:
            continue
        dtype_str = str(gdf[col].dtype)
        qtype = dtype_mapping.get(dtype_str, QVariant.String)
        fields.append(QgsField(col, qtype))
    return fields


def write_gdf_to_sink(gdf, sink):
    """Écrit chaque ligne du GeoDataFrame comme entité dans le sink."""
    geom_col = gdf.geometry.name
    attr_cols = [c for c in gdf.columns if c != geom_col]

    for _, row in gdf.iterrows():
        feat = QgsFeature()
        geom = QgsGeometry.fromWkt(row[geom_col].wkt)
        feat.setGeometry(geom)

        attrs = []
        for col in attr_cols:
            val = row[col]
            # Cast des types non supportés nativement par QVariant
            if hasattr(val, "item"):  # numpy scalar -> python natif
                val = val.item()
            attrs.append(val)
        feat.setAttributes(attrs)

        sink.addFeature(feat)
#%%GTFS
def seconds_to_hms(val):
    """Reconvertit les secondes (format interne Partridge) en HH:MM:SS 
    pour pouvoir les relire ensuite."""
    if pd.isna(val) or val == "":
        return val
    try:
        total_seconds = int(float(val))
    except (ValueError, TypeError):
        return val  # déjà une chaîne HH:MM:SS ou valeur non numérique
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

