import functions_framework
import requests
from bs4 import BeautifulSoup
import pandas as pd
from google.cloud import storage

BUCKET_NAME = 'development_awarri'           # Replace with your actual GCS bucket name
DESTINATION_BLOB_NAME = 'books.csv'        # GCS destination path
LOCAL_CSV_FILE = '/tmp/books.csv'  


def scrape_books():
    url = "http://books.toscrape.com/catalogue/page-1.html"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    books = []
    for article in soup.select("article.product_pod"):
        title = article.h3.a["title"]
        price = article.select_one(".price_color").text
        books.append({"Title": title, "Price": price})

    return pd.DataFrame(books)

# -------- SAVE TO CSV --------
def save_to_csv(df, filename):
    df.to_csv(filename, index=False)
    print(f"Saved data to {filename}")
    
    
    
# ======================== GCP SPECIFICITY ==========================

# -------- UPLOAD TO GCP --------
def upload_to_gcs(local_file, bucket_name, destination_blob):
    # Set up credentials

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob)

    blob.upload_from_filename(local_file)
    print(f"Uploaded {local_file} to gs://{bucket_name}/{destination_blob}")



@functions_framework.http
def hello_http(request):
    """HTTP Cloud Function.
    Args:
        request (flask.Request): The request object.
        <https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data>
    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`
        <https://flask.palletsprojects.com/en/1.1.x/api/#flask.make_response>.
    """
    request_json = request.get_json(silent=True)
    request_args = request.args

    df = scrape_books()
    save_to_csv(df, LOCAL_CSV_FILE)
    upload_to_gcs(LOCAL_CSV_FILE, BUCKET_NAME, DESTINATION_BLOB_NAME)

    if request_json and 'name' in request_json:
        name = request_json['name']
    elif request_args and 'name' in request_args:
        name = request_args['name']
    else:
        name = 'World'
    return 'Hello {}!'.format(name)
