For the installation of the plugins you might need to install the `matplotlib` library before installation:

Open the python console from the Plugins menu. In the console execute:

```
import pip
pip.main(["install","matplotlib"])
```

## Processing scripts

`v3/scripts/load_s3_prefix.py` adds every raster/vector under an S3 prefix to the current project via GDAL's `/vsis3/` (COGs are streamed, nothing is downloaded).

Install: Processing Toolbox -> Scripts (Python icon) -> Add Script to Toolbox..., then run "Load S3 prefix" from Scripts > Earth Big Data. Credentials come from the standard AWS chain (env vars, `~/.aws/credentials`, IAM role); tick "Anonymous access" for public buckets.
