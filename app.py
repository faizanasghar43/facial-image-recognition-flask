from flask import Flask, request, render_template, jsonify, redirect
import face_recognition
import pandas as pd
import datetime
import os
import base64

app = Flask(__name__)
UPLOAD_FOLDER = 'uploaded_images'
ENCODINGS_FILE = 'face_encodings.csv'

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Ensure the encodings file exists
if not os.path.exists(ENCODINGS_FILE):
    pd.DataFrame(columns=['username', 'check_in_time', 'face_encoding']).to_csv(ENCODINGS_FILE, index=False)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/process_image', methods=['POST'])
def process_image():
    print("Processing image...")
    data = request.json['image']
    header, encoded = data.split(",", 1)
    image_data = base64.b64decode(encoded)

    image_path = os.path.join(UPLOAD_FOLDER, 'temp_image.png')
    with open(image_path, 'wb') as file:
        file.write(image_data)

    image = face_recognition.load_image_file(image_path)
    encodings = face_recognition.face_encodings(image)
    if encodings:
        face_encoding = encodings[0]
        df = pd.read_csv(ENCODINGS_FILE)
        for i, row in df.iterrows():
            known_face_encoding = [float(x) for x in row['face_encoding'][1:-1].split(', ')]
            if face_recognition.compare_faces([known_face_encoding], face_encoding)[0]:
                last_seen_time = row['check_in_time']  # Store the last seen time
                print(last_seen_time)
                # Update the check_in_time to current time
                df.at[i, 'check_in_time'] = datetime.datetime.now()
                df.to_csv(ENCODINGS_FILE, index=False)
                return jsonify(status='found', last_seen=last_seen_time,
                               username=row['username'])  # Return the last seen time
        # Face not found, save the encoding to use it when the user submits their info
        os.rename(image_path, os.path.join(UPLOAD_FOLDER, 'new_face.png'))
        return jsonify(status='not_found')
    else:
        return jsonify(status='error', message='No face detected'), 400


# @app.route('/process_image', methods=['POST'])
# def process_image():
#     data = request.json['image']
#     header, encoded = data.split(",", 1)
#     image_data = base64.b64decode(encoded)
#
#     image_path = os.path.join(UPLOAD_FOLDER, 'temp_image.png')
#     with open(image_path, 'wb') as file:
#         file.write(image_data)
#
#     image = face_recognition.load_image_file(image_path)
#     encodings = face_recognition.face_encodings(image)
#     if encodings:
#         face_encoding = encodings[0]
#         df = pd.read_csv(ENCODINGS_FILE)
#         for i, row in df.iterrows():
#             known_face_encoding = [float(x) for x in row['face_encoding'][1:-1].split(', ')]
#             if face_recognition.compare_faces([known_face_encoding], face_encoding)[0]:
#                 df.at[i, 'check_in_time'] = datetime.datetime.now()
#                 df.to_csv(ENCODINGS_FILE, index=False)
#                 return jsonify(status='found', last_seen=row['check_in_time'])
#         # Face not found, save the encoding to use it when the user submits their info
#         os.rename(image_path, os.path.join(UPLOAD_FOLDER, 'new_face.png'))
#         return jsonify(status='not_found')
#     else:
#         return jsonify(status='error', message='No face detected'), 400


@app.route('/add_info', methods=['GET', 'POST'])
def add_info():
    if request.method == 'POST':
        username = request.form['username']
        df = pd.read_csv(ENCODINGS_FILE)
        face_encoding = \
            face_recognition.face_encodings(
                face_recognition.load_image_file(os.path.join(UPLOAD_FOLDER, 'new_face.png')))[
                0]
        new_row = pd.DataFrame([{'username': username, 'check_in_time': datetime.datetime.now(),
                                 'face_encoding': str(face_encoding.tolist())}])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(ENCODINGS_FILE, index=False)
        os.remove(os.path.join(UPLOAD_FOLDER, 'new_face.png'))  # Remove the temp image file
        return redirect('/')
    else:
        return render_template('add_info.html')


@app.route('/add_user_info', methods=['POST'])
def add_user_info():
    username = request.form['username']
    df = pd.read_csv(ENCODINGS_FILE)

    # Ensure the new face image exists
    new_face_path = os.path.join(UPLOAD_FOLDER, 'new_face.png')
    if not os.path.exists(new_face_path):
        return 'Error: No new face data found.', 400

    # Load the new face encoding
    face_encoding = face_recognition.face_encodings(face_recognition.load_image_file(new_face_path))[0]

    # Add a new row with the new user info and face encoding
    new_row = pd.DataFrame([{
        'username': username,
        'check_in_time': datetime.datetime.now(),
        'face_encoding': str(face_encoding.tolist())
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(ENCODINGS_FILE, index=False)

    # Remove the temp new face image file after processing
    os.remove(new_face_path)

    # Redirect to the index page after adding the new user info
    return redirect('/')


# @app.route('/add_info', methods=['GET', 'POST'])
# def add_info():
#     if request.method == 'POST':
#         username = request.form['username']
#         df = pd.read_csv(ENCODINGS_FILE)
#
#         # Ensure the new face image exists
#         new_face_path = os.path.join(UPLOAD_FOLDER, 'new_face.png')
#         if not os.path.exists(new_face_path):
#             return 'Error: No new face data found.', 400
#
#         # Load the new face encoding
#         face_encoding = face_recognition.face_encodings(face_recognition.load_image_file(new_face_path))[0]
#
#         # Add a new row with the new user info and face encoding
#         new_row = pd.DataFrame([{
#             'username': username,
#             'check_in_time': datetime.datetime.now(),
#             'face_encoding': str(face_encoding.tolist())
#         }])
#         df = pd.concat([df, new_row], ignore_index=True)
#         df.to_csv(ENCODINGS_FILE, index=False)
#
#         # Remove the temp new face image file after processing
#         os.remove(new_face_path)
#
#         # Redirect to the index page after adding the new user info
#         return redirect('/')
#     else:
#         # Display the form to add new user info
#         return render_template('add_info.html')
if __name__ == '__main__':
    app.run(debug=True, port=8000)
