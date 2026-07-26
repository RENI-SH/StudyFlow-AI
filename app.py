from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import PyPDF2
import re

app = Flask(__name__)
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
    
    # Extract definitions
    def_found = False
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 20: continue
        if re.search(r'\b(define|definition|means|refers to|is defined as|consists of|called|known as)\b', sentence, re.IGNORECASE):
            html += f"<p><i>\"{sentence}\"</i></p>"
            def_found = True
    
    if not def_found:
        html += f"<p><i>\"Key concepts from {subject} - {topic}\"</i></p>"
    
    # Extract Questions and Answers
    html += "<h3>Questions & Answers</h3>"
    qa_found = False
    for sentence in sentences:
        sentence = sentence.strip()
        if '?' in sentence and len(sentence) > 15:
            html += f"<p><b>Q:</b> {sentence}</p>"
            qa_found = True
    
    if not qa_found:
        html += "<p><i>Refer to your notes for practice questions.</i></p>"
    
    # Topic-wise theory with minimal spacing
    html += "<h3>Detailed Theory</h3>"
    
    # Group sentences by topics (capitalize first word as topic marker)
    current_topic = None
    topic_points = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 15: continue
        
        # Skip if already used as definition or question
        if re.search(r'\b(define|definition|means|refers to)\b', sentence, re.IGNORECASE):
            continue
        if '?' in sentence:
            continue
            
        # Check if this looks like a topic header (starts with capital, short)
        if sentence[0].isupper() and len(sentence) < 60 and not sentence[0:5].lower() in ['the', 'this', 'that']:
            # New topic
            if current_topic and topic_points:
                # Write previous topic
                html += f"<p><b>{current_topic}</b></p>"
                for point in topic_points:
                    html += f"<p>• {point}</p>"
                html += ""  # Minimal spacing
            current_topic = sentence.rstrip('.')
            topic_points = []
        else:
            # Add to current topic
            if len(sentence) > 20:
                topic_points.append(sentence)
    
    # Write last topic
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

        # FALLBACK if no text extracted
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

if __name__ == '__main__':
    app.run(debug=True)