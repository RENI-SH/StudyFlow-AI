from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import PyPDF2
import re
import os

# CRITICAL: template_folder='.' tells Flask to look in the main folder for your HTML files
app = Flask(__name__, template_folder='.')
app.secret_key = 'studyflow_secret_key_123'

summary_data = {
    'subject': '',
    'topic': '',
    'html_content': ''
}

@app.route('/')
def home():
    return render_template('welcome.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', 'Guest')
        session['username'] = username
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/guest')
def guest_login():
    session['username'] = 'Guest User'
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    if 'username' not in session: return redirect(url_for('login'))
    return render_template('dashboard.html', username=session['username'])

@app.route('/focus')
def focus():
    if 'username' not in session: return redirect(url_for('login'))
    return render_template('focus.html', username=session['username'])

@app.route('/notefusion')
def notefusion():
    if 'username' not in session: return redirect(url_for('login'))
    return render_template('notefusion.html', username=session['username'])

@app.route('/timetable')
def timetable():
    if 'username' not in session: return redirect(url_for('login'))
    return render_template('timetable.html', username=session['username'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

def extract_text_from_file(file):
    text = ""
    filename = file.filename.lower()
    try:
        if filename.endswith('.pdf'):
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted: text += extracted + "\n"
        elif filename.endswith('.txt'):
            text = file.read().decode('utf-8')
        elif filename.endswith(('.ppt', '.pptx')):
            text = file.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Error reading {file.filename}: {e}")
    return text

def smart_local_formatter(text, subject, topic):
    sentences = re.split(r'(?<=[.!?]) +', text.replace('\n', ' '))
    
    html = f"<h2>{subject}: {topic}</h2>"
    html += "<h3>Key Definitions</h3>"
    
    def_found = False
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 20: continue
        if re.search(r'\b(define|definition|means|refers to|is defined as|consists of|called|known as)\b', sentence, re.IGNORECASE):
            html += f"<p><i>\"{sentence}\"</i></p>"
            def_found = True
    
    if not def_found:
        html += f"<p><i>\"Key concepts from {subject} - {topic}\"</i></p>"
    
    html += "<h3>Questions & Answers</h3>"
    qa_found = False
    for sentence in sentences:
        sentence = sentence.strip()
        if '?' in sentence and len(sentence) > 15:
            html += f"<p><b>Q:</b> {sentence}</p>"
            qa_found = True
    
    if not qa_found:
        html += "<p><i>Refer to your notes for practice questions.</i></p>"
    
    html += "<h3>Detailed Theory</h3>"
    
    current_topic = None
    topic_points = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 15: continue
        
        if re.search(r'\b(define|definition|means|refers to)\b', sentence, re.IGNORECASE):
            continue
        if '?' in sentence:
            continue
            
        if sentence[0].isupper() and len(sentence) < 60 and not sentence[0:5].lower() in ['the', 'this', 'that']:
            if current_topic and topic_points:
                html += f"<p><b>{current_topic}</b></p>"
                for point in topic_points:
                    html += f"<p>• {point}</p>"
            current_topic = sentence.rstrip('.')
            topic_points = []
        else:
            if len(sentence) > 20:
                topic_points.append(sentence)
    
    if current_topic and topic_points:
        html += f"<p><b>{current_topic}</b></p>"
        for point in topic_points:
            html += f"<p>• {point}</p>"
    
    return html

@app.route('/api/summarize', methods=['POST'])
def summarize():
    try:
        subject = request.form.get('subject')
        topic = request.form.get('topic')
        files = request.files.getlist('files')
        
        if not files: return jsonify({'error': 'No files uploaded'}), 400

        all_text = ""
        for file in files:
            extracted = extract_text_from_file(file)
            if extracted.strip():
                all_text += f"\n--- From {file.filename} ---\n{extracted}\n"

        if not all_text.strip():
            all_text = f"""
{subject} - {topic} is an important area of study.

Key concepts include fundamental principles and theories.

What is {topic}? It refers to the study of specific scientific principles.

Important points:
- The core principles form the foundation.
- Understanding relationships is crucial.
- Practical applications demonstrate relevance.

How does it work? The mechanism involves several key processes.

Why is it important? Because it helps us understand fundamental phenomena.
            """

        html_content = smart_local_formatter(all_text, subject, topic)

        summary_data['subject'] = subject
        summary_data['topic'] = topic
        summary_data['html_content'] = html_content

        return jsonify({'success': True, 'redirect': f'/results?subject={subject}&topic={topic}'})
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/results')
def results():
    if 'username' not in session: return redirect(url_for('login'))
    return render_template('results.html', username=session['username'])

@app.route('/api/get-summary-data')
def get_summary_data():
    html = summary_data.get('html_content', '<p>No content generated</p>')
    return jsonify({'html': html})

# CRITICAL FOR RENDER DEPLOYMENT
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
