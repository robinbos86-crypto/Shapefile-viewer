from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
import geopandas as gpd
import tempfile
import zipfile
import os
import shutil

app = FastAPI()


@app.get("/")
def home():
    return FileResponse("static/index.html")


@app.post("/upload")
async def upload_shapefile(file: UploadFile = File(...)):

    # Controleer bestandstype
    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail="Upload een ZIP-bestand met een Shapefile."
        )

    # Tijdelijke directory maken
    temp_dir = tempfile.mkdtemp()

    try:
        zip_path = os.path.join(temp_dir, "upload.zip")

        # ZIP opslaan
        with open(zip_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # ZIP uitpakken
        extract_dir = os.path.join(temp_dir, "extracted")
        os.makedirs(extract_dir)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

        # Zoek naar .shp-bestand
        shp_file = None

        for root, dirs, files in os.walk(extract_dir):
            for filename in files:
                if filename.lower().endswith(".shp"):
                    shp_file = os.path.join(root, filename)
                    break

            if shp_file:
                break

        if not shp_file:
            raise HTTPException(
                status_code=400,
                detail="Geen .shp-bestand gevonden in de ZIP."
            )

        # Shapefile openen
        gdf = gpd.read_file(shp_file)

        if gdf.empty:
            raise HTTPException(
                status_code=400,
                detail="De Shapefile bevat geen objecten."
            )

        # Controleer CRS
        if gdf.crs is None:
            raise HTTPException(
                status_code=400,
                detail="De Shapefile heeft geen CRS (.prj)."
            )

        # Omzetten naar WGS84 voor Leaflet
        gdf = gdf.to_crs(epsg=4326)

        # GeoJSON maken
        geojson = gdf.to_json()

        return {
            "filename": file.filename,
            "features": len(gdf),
            "geojson": geojson
        }

    except zipfile.BadZipFile:
        raise HTTPException(
            status_code=400,
            detail="Het bestand is geen geldige ZIP."
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Fout bij verwerken van Shapefile: {str(e)}"
        )

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)