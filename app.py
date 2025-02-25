from flask import Flask, request, jsonify, render_template
import boto3
import os
from botocore.exceptions import NoCredentialsError

app = Flask(__name__)

# AWS Configuration
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")  # Ensure these are set in your environment
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME", "secureshare7")
AWS_REGION = os.getenv("AWS_REGION", "eu-north-1")

# Initialize S3 client
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION
)

# Constants for file validation
ALLOWED_EXTENSIONS = {"txt", "pdf", "png", "jpg", "jpeg", "gif"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

# Helper functions
def allowed_file(filename):
    """Check if the file has an allowed extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_file_size(file):
    """Check if the file size is within the allowed limit."""
    file.seek(0, os.SEEK_END)  # Move to the end of the file
    file_length = file.tell()  # Get the file size
    file.seek(0)  # Reset file pointer to the beginning
    return file_length <= MAX_FILE_SIZE

# Routes
@app.route("/")
def home():
    """Render the homepage."""
    return render_template("index.html")

@app.route("/generate-presigned-url", methods=["POST"])
def generate_presigned_url():
    """Generate a presigned URL for file uploads."""
    data = request.json
    file_name = data.get("file_name")
    file_type = data.get("file_type")

    if not file_name or not file_type:
        return jsonify({"error": "File name and type are required"}), 400

    try:
        presigned_url = s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": AWS_BUCKET_NAME,
                "Key": file_name,
                "ContentType": file_type
            },
            ExpiresIn=300  # URL expires in 5 minutes
        )
        return jsonify({"url": presigned_url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/upload", methods=["POST"])
def upload_file():
    """Handle file uploads."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    file_name = file.filename

    if not allowed_file(file_name):
        return jsonify({"error": "File type not allowed"}), 400

    if not allowed_file_size(file):
        return jsonify({"error": "File size exceeds limit"}), 400

    try:
        s3_client.upload_fileobj(file, AWS_BUCKET_NAME, file_name)
        file_url = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{file_name}"
        return jsonify({"message": "File uploaded successfully", "url": file_url})
    except NoCredentialsError:
        return jsonify({"error": "AWS credentials not found"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/get-presigned-download-url", methods=["POST"])
def get_presigned_download_url():
    """Generate a presigned URL for file downloads."""
    data = request.json
    file_name = data.get("file_name")
    password = data.get("password")  # Add password validation logic (e.g., check against a database)

    if not file_name:
        return jsonify({"error": "File name is required"}), 400

    try:
        presigned_url = s3_client.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": AWS_BUCKET_NAME,
                "Key": file_name
            },
            ExpiresIn=300  # URL expires in 5 minutes
        )
        return jsonify({"url": presigned_url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/list-uploaded-files", methods=["GET"])
def list_uploaded_files():
    """Fetch the list of uploaded files from S3."""
    try:
        response = s3_client.list_objects_v2(Bucket=AWS_BUCKET_NAME)
        files = [item["Key"] for item in response.get("Contents", [])]
        return jsonify({"files": files})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Run the app
if __name__ == "__main__":
    app.run(debug=True)