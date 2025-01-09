from flask import Flask, render_template, request, send_file
import requests
import os
import threading
import time

app = Flask(__name__)
BASE_URL = "https://api.penpencil.xyz"

def get_headers(auth_code):
    return {
        'authorization': f"Bearer {auth_code}",
        'client-id': '5eb393ee95fab7468a79d189',
        'content-type': 'application/json',
    }

def get_batches(auth_code):
    response = requests.get(
        f"{BASE_URL}/v3/batches/my-batches", 
        headers=get_headers(auth_code)
    )
    return response.json().get("data", [])

def get_subjects(batch_id, auth_code):
    response = requests.get(
        f"{BASE_URL}/v3/batches/{batch_id}/details", 
        headers=get_headers(auth_code)
    )
    return response.json().get("data", {}).get("subjects", [])

def get_content_by_type(batch_id, subject_id, page, content_type, auth_code):
    params = {
        'page': page,
        'tag': '',
        'contentType': content_type,
        'ut': ''
    }
    
    response = requests.get(
        f"{BASE_URL}/v2/batches/{batch_id}/subject/{subject_id}/contents",
        params=params,
        headers=get_headers(auth_code)
    )
    return response.json().get("data", [])

def process_content(data, content_type):
    processed_data = []
    
    if content_type == "exercises-notes-videos":
        for item in data:
            processed_data.append({
                'title': item['topic'],
                'url': item['url'].strip()
            })
            
    elif content_type == "notes":
        for item in data:
            if item.get('homeworkIds'):
                homework = item['homeworkIds'][0]
                if homework.get('attachmentIds'):
                    attachment = homework['attachmentIds'][0]
                    processed_data.append({
                        'title': homework['topic'].replace('|', ' ').replace(':', ' '),
                        'url': attachment['baseUrl'] + attachment['key']
                    })
                    
    elif content_type == "DppNotes":
        for item in data:
            if item.get('homeworkIds'):
                for homework in item['homeworkIds']:
                    if homework.get('attachmentIds'):
                        attachment = homework['attachmentIds'][0]
                        processed_data.append({
                            'title': homework['topic'].replace('|', ' ').replace(':', ' '),
                            'url': attachment['baseUrl'] + attachment['key']
                        })
                        
    elif content_type == "DppSolution":
        for item in data:
            url = item['url'].replace("d1d34p8vz63oiq", "d26g5bnklkwsh4").replace("mpd", "m3u8").strip()
            processed_data.append({
                'title': item['topic'].replace(':', ' '),
                'url': url,
                'image': item['videoDetails']['image']
            })
            
    return processed_data

def save_content_to_file(batch_name, subject_name, content_type, content_data):
    filename = f"{batch_name}_{subject_name}_{content_type}.txt"
    with open(filename, 'w', encoding='utf-8') as file:
        for item in content_data:
            if 'image' in item:
                file.write(f"{item['title']}: {item['url']}: {item['image']}\n")
            else:
                file.write(f"{item['title']}: {item['url']}\n")
    return filename

def schedule_file_deletion(file_path, delay=300):
    def delete_file():
        time.sleep(delay)
        if os.path.exists(file_path):
            os.remove(file_path)
    threading.Thread(target=delete_file).start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/batches', methods=['POST'])
def batches():
    auth_code = request.form['auth_code']
    batches_data = get_batches(auth_code)
    return render_template('batches.html', batches=batches_data, auth_code=auth_code)

@app.route('/subjects', methods=['POST'])
def subjects():
    auth_code = request.form['auth_code']
    batch_id = request.form['batch_id']
    subjects_data = get_subjects(batch_id, auth_code)
    return render_template('subjects.html', subjects=subjects_data, batch_id=batch_id, auth_code=auth_code)

@app.route('/contents', methods=['POST'])
def contents():
    auth_code = request.form['auth_code']
    batch_id = request.form['batch_id']
    subject_id = request.form['subject_id']
    subject_name = request.form['subject_name']
    content_type = request.form.get('content_type', 'exercises-notes-videos')
    
    page = 1
    all_data = []
    
    while True:
        data = get_content_by_type(batch_id, subject_id, page, content_type, auth_code)
        if not data:
            break
        processed_data = process_content(data, content_type)
        all_data.extend(processed_data)
        page += 1

    batch_name = f"Batch_{batch_id}"
    filename = save_content_to_file(batch_name, subject_name, content_type, all_data)
    schedule_file_deletion(os.path.join(os.getcwd(), filename))
    
    return render_template('contents.html', filename=filename)

@app.route('/download/<filename>', methods=['GET'])
def download(filename):
    file_path = os.path.join(os.getcwd(), filename)
    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)