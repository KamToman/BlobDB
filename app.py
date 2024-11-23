from flask import Flask, request, jsonify
from azure.storage.blob import BlobServiceClient
from azure.cosmos import CosmosClient, PartitionKey
from datetime import datetime
from flask_cors import CORS  # Importowanie CORS
import os

app = Flask(__name__)

# Konfiguracja CORS
CORS(app)  # Włączenie CORS dla całej aplikacji

# Azure Blob Storage configuration
BLOB_CONNECTION_STRING = "DefaultEndpointsProtocol=https;AccountName=blobtest87340;AccountKey=82o1gC/PXkq5dvRu23uEqkE5ZPjkcIi+tRwBpi2pJo/u0tnr+yJrZ9BBQWNCExbHngSiNk87rkxl+AStr9BhOg==;EndpointSuffix=core.windows.net"
BLOB_CONTAINER_NAME = "files"
blob_service_client = BlobServiceClient.from_connection_string(BLOB_CONNECTION_STRING)
blob_container_client = blob_service_client.get_container_client(BLOB_CONTAINER_NAME)

# Azure Cosmos DB configuration
COSMOS_ENDPOINT = "https://cosmosdb-blobtest.documents.azure.com:443/"
COSMOS_KEY = "yLuM3vUSs8tmGFoiOdvBrLi14FCthsDXoZAg1r73rUgNm8XKspypFj7wvvDuFyT5ntDiLcB4LhuoACDbZWej2g=="
DATABASE_NAME = "BlobCosmosDB"
CONTAINER_NAME = "DBContainer"

cosmos_client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
cosmos_database = cosmos_client.create_database_if_not_exists(DATABASE_NAME)
cosmos_container = cosmos_database.create_container_if_not_exists(
    id=CONTAINER_NAME,
    partition_key=PartitionKey(path="/id"),
    offer_throughput=400
)


@app.route("/upload", methods=["POST"])
def upload_file():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file provided"}), 400

    # Save file to Azure Blob Storage
    blob_name = file.filename
    blob_client = blob_container_client.get_blob_client(blob_name)
    blob_client.upload_blob(file, overwrite=True)

    # Save metadata to Cosmos DB
    metadata = {
        "id": blob_name,
        "name": blob_name,
        "type": file.content_type,
        "upload_date": datetime.utcnow().isoformat()
    }
    cosmos_container.upsert_item(metadata)

    return jsonify({"message": "File uploaded successfully", "metadata": metadata})


@app.route("/files", methods=["GET"])
def list_files():
    query = "SELECT * FROM c"
    files = list(cosmos_container.query_items(query=query, enable_cross_partition_query=True))
    return jsonify(files)


@app.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    blob_client = blob_container_client.get_blob_client(filename)
    blob_data = blob_client.download_blob().readall()

    return blob_data, 200, {
        "Content-Disposition": f"attachment; filename={filename}"
    }


if __name__ == "__main__":
    # Pobranie portu z zmiennej środowiskowej PORT lub ustawienie domyślnego 8000
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=True)
