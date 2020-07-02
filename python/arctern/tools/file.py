# Copyright (C) 2019-2020 Zilliz. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# pylint: disable=too-many-lines
# pylint: disable=too-many-public-methods, unused-argument, redefined-builtin
import json
import warnings
import fiona
import numpy as np
from arctern import GeoSeries
import pandas as pd


def _read_file(filename, bbox=None, mask=None, rows=None, **kwargs):
    with fiona.Env():
        with fiona.open(filename, "r", **kwargs) as features:
            crs = (
                features.crs["init"]
                if features.crs and "init" in features.crs
                else features.crs_wkt
            )
            if mask is not None:
                if isinstance(mask, (str, bytes)):
                    mask = GeoSeries(mask).unary_union()
                if not isinstance(mask, GeoSeries):
                    raise TypeError(f"unsupported mask type {type(mask)}")
                mask = mask.as_geojson()[0]
            if rows is not None:
                if isinstance(rows, int):
                    rows = slice(rows)
                elif not isinstance(rows, slice):
                    raise TypeError("'rows' must be an integer or a slice.")
                f_filter = features.filter(
                    rows.start, rows.stop, rows.step, bbox=bbox, mask=mask
                )
            elif any((bbox, mask)):
                f_filter = features.filter(bbox=bbox, mask=mask)
            else:
                f_filter = features

            columns = list(features.schema["properties"])
            if kwargs.get("ignore_geometry", False):
                return pd.DataFrame(
                    [record["properties"] for record in f_filter], columns=columns
                )
            return _from_features(f_filter, crs=crs, columns=columns + ["geometry"])


def _from_features(features, crs=None, columns=None):
    from arctern import GeoDataFrame
    rows = []
    for feature in features:
        if hasattr(feature, "__geo_interface__"):
            feature = feature.__geo_interface__
        row = {
            "geometry": GeoSeries.geom_from_geojson(json.dumps(feature["geometry"]))[0] if feature["geometry"] else None
        }
        # load properties
        row.update(feature["properties"])
        rows.append(row)
    return GeoDataFrame(rows, columns=columns, geometries=["geometry"], crs=[crs])


def read_file(*args, **kwargs):
    return _read_file(*args, **kwargs)


def get_geom_types(geoseries):
    geom_types = []
    for geom_type in geoseries.geom_type:
        geom_type = geom_type[3:].title()
        if geom_type is not None and geom_type not in geom_types:
            geom_types.append(geom_type)
    if len(geom_types) == 1:
        return geom_types[0]
    else:
        return geom_types


def infer_schema(df, geo_col):
    from collections import OrderedDict

    types = {"Int64": "int", "string": "str", "boolean": "bool"}

    def convert_type(column, in_type):
        if in_type == object:
            return "str"
        if in_type.name.startswith("datatime64"):
            return "datetime"
        if str(in_type) in types:
            out_type = types[str(in_type)]
        else:
            out_type = type(np.zeros(1, in_type).item()).__name__
        if out_type == "long":
            out_type = "int"
        return out_type

    properties = OrderedDict(
        [
            (col, convert_type(col, _type))
            for col, _type in zip(df.columns, df.dtypes)
            if col != geo_col
        ]
    )

    geo_type = get_geom_types(df[geo_col])

    schema = {"geometry": geo_type, "properties": properties}

    return schema


def _to_file(
        df,
        filename,
        driver="ESRI Shapefile",
        schema=None,
        index=None,
        mode="w",
        crs=None,
        col=None,
        **kwargs
):
    copy_df = df.copy()
    copy_df[col].set_crs(df[col].crs)
    for col_name in copy_df._geometry_column_name:
        if col_name is not col:
            copy_df[col_name] = pd.Series(copy_df[col_name].to_wkt())

    if index is None:
        index = list(copy_df.index.names) != [None] or type(copy_df.index) not in (
            pd.RangeIndex,
            pd.Int64Index,
        )
    if index:
        copy_df = copy_df.reset_index(drop=False)
    if schema is None:
        schema = infer_schema(copy_df, col)
    if not crs:
        crs = copy_df[col].crs

    if driver == "ESRI Shapefile" and any([len(c) > 10 for c in copy_df.columns.tolist()]):
        warnings.warn(
            "Column names longer than 10 characters will be truncated when saved to "
            "ESRI Shapefile.",
            stacklevel=3,
        )

    with fiona.Env():
        with fiona.open(
                filename, mode=mode, driver=driver, crs_wkt=crs, schema=schema, **kwargs
        ) as colxn:
            colxn.writerecords(copy_df.iterfeatures(col=col))


def to_file(*args, **kwargs):
    return _to_file(*args, **kwargs)
