"""
Load S3 Prefix - QGIS Processing script

Adds every raster/vector found under an S3 prefix to the current project via
GDAL's /vsis3/ handler (COGs are streamed, nothing is downloaded).

Install: Processing Toolbox -> Scripts (Python icon) -> Add Script to Toolbox...
Then run "Load S3 prefix" from Scripts > Earth Big Data.

Credentials: uses the standard AWS chain (env vars, ~/.aws/credentials, IAM role)
as read by GDAL. Tick "Anonymous access" for public buckets.
"""

from osgeo import gdal
from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
    QgsProject,
    QgsRasterLayer,
    QgsVectorLayer,
)

VECTOR_EXTS = {".gpkg", ".geojson", ".json", ".shp", ".fgb", ".parquet", ".kml", ".gdb"}


class LoadS3Prefix(QgsProcessingAlgorithm):
    PREFIX = "PREFIX"
    EXTENSIONS = "EXTENSIONS"
    RECURSIVE = "RECURSIVE"
    ANON = "ANON"
    REGION = "REGION"
    ENDPOINT = "ENDPOINT"
    MAX_LAYERS = "MAX_LAYERS"
    GROUP = "GROUP"

    def name(self):
        return "load_s3_prefix"

    def displayName(self):
        return "Load S3 prefix"

    def group(self):
        return "Earth Big Data"

    def groupId(self):
        return "ebd"

    def shortHelpString(self):
        return (
            "Lists objects under an S3 prefix (s3://bucket/path/) and adds each "
            "file matching the extension filter to the project as a layer, via "
            "/vsis3/. Rasters and vectors are detected by extension."
        )

    def flags(self):
        # Layers are added to the project directly, so run on the main thread.
        return super().flags() | QgsProcessingAlgorithm.FlagNoThreading

    def createInstance(self):
        return LoadS3Prefix()

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterString(self.PREFIX, "S3 prefix (s3://bucket/path/)"))
        self.addParameter(QgsProcessingParameterString(self.EXTENSIONS, "Extensions (comma separated)", defaultValue=".tif,.tiff"))
        self.addParameter(QgsProcessingParameterBoolean(self.RECURSIVE, "Search sub-prefixes", defaultValue=False))
        self.addParameter(QgsProcessingParameterBoolean(self.ANON, "Anonymous access (public bucket)", defaultValue=False))
        self.addParameter(QgsProcessingParameterString(self.REGION, "AWS region (optional)", optional=True))
        self.addParameter(QgsProcessingParameterString(self.ENDPOINT, "Custom endpoint (optional, e.g. MinIO)", optional=True))
        self.addParameter(QgsProcessingParameterNumber(self.MAX_LAYERS, "Max layers to load", type=QgsProcessingParameterNumber.Integer, defaultValue=100, minValue=1))
        self.addParameter(QgsProcessingParameterBoolean(self.GROUP, "Put layers in a group", defaultValue=True))

    def processAlgorithm(self, parameters, context, feedback):
        prefix = self.parameterAsString(parameters, self.PREFIX, context).strip()
        if not prefix.startswith("s3://"):
            raise QgsProcessingException("Prefix must start with s3://")
        if not prefix.endswith("/"):
            prefix += "/"

        exts = tuple(
            e.strip().lower() if e.strip().startswith(".") else "." + e.strip().lower()
            for e in self.parameterAsString(parameters, self.EXTENSIONS, context).split(",")
            if e.strip()
        )
        recursive = self.parameterAsBool(parameters, self.RECURSIVE, context)
        max_layers = self.parameterAsInt(parameters, self.MAX_LAYERS, context)
        region = self.parameterAsString(parameters, self.REGION, context)
        endpoint = self.parameterAsString(parameters, self.ENDPOINT, context)

        if self.parameterAsBool(parameters, self.ANON, context):
            gdal.SetConfigOption("AWS_NO_SIGN_REQUEST", "YES")
        else:
            gdal.SetConfigOption("AWS_NO_SIGN_REQUEST", None)
        if region:
            gdal.SetConfigOption("AWS_REGION", region)
        if endpoint:
            gdal.SetConfigOption("AWS_S3_ENDPOINT", endpoint)
        gdal.SetConfigOption("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")

        vsi_root = "/vsis3/" + prefix[len("s3://"):]
        feedback.pushInfo(f"Listing {vsi_root}")
        entries = gdal.ReadDirRecursive(vsi_root) if recursive else gdal.ReadDir(vsi_root)
        if entries is None:
            raise QgsProcessingException(
                "Could not list the prefix. Check the path, region and credentials "
                "(or tick Anonymous access for public buckets)."
            )

        files = sorted(
            e for e in entries
            if not e.endswith("/") and e.lower().endswith(exts)
        )
        if not files:
            feedback.pushWarning("No matching files found.")
            return {}
        if len(files) > max_layers:
            feedback.pushWarning(f"{len(files)} matches; loading first {max_layers}.")
            files = files[:max_layers]

        project = QgsProject.instance()
        parent = project.layerTreeRoot()
        if self.parameterAsBool(parameters, self.GROUP, context):
            parent = parent.insertGroup(0, prefix.rstrip("/").split("/")[-1] or "s3")

        loaded = 0
        for i, rel in enumerate(files):
            if feedback.isCanceled():
                break
            uri = vsi_root + rel
            name = rel.rsplit("/", 1)[-1]
            ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
            if ext in VECTOR_EXTS:
                layer = QgsVectorLayer(uri, name, "ogr")
            else:
                layer = QgsRasterLayer(uri, name, "gdal")
            if not layer.isValid():
                feedback.pushWarning(f"Could not open {uri}")
                continue
            project.addMapLayer(layer, False)
            parent.addLayer(layer)
            loaded += 1
            feedback.setProgress(100 * (i + 1) / len(files))

        feedback.pushInfo(f"Loaded {loaded} of {len(files)} layers.")
        return {}
