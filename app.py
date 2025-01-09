from flask import Flask, render_template, request
import spacy
from spacy import displacy
from markdown import markdown
from sklearn.metrics import precision_score, recall_score, f1_score, accuracy_score
import json

nlp = spacy.load('en_core_web_sm')

HTML_WRAPPER = """<div style="overflow-x: auto; border: 1px solid #e6e9ef; border-radius: 0.25rem; padding: 1rem">{}</div>"""

app = Flask(__name__)

def calculate_metrics(pred_entities, true_entities, text_length):
    """
    Calculate precision, recall, F1 score, and accuracy for NER predictions
    """
    pred_bio = [0] * text_length
    true_bio = [0] * text_length
    
    # If no predicted entities, set accuracy to 0
    if not pred_entities:
        return {
            'precision': 0.0,
            'recall': 0.0,
            'f1_score': 0.0,
            'accuracy': 0.0
        }

    for ent in pred_entities:
        for i in range(ent['start'], ent['end']):
            if i < len(pred_bio):
                pred_bio[i] = 1
    
    for ent in true_entities:
        for i in range(ent['start'], ent['end']):
            if i < len(true_bio):
                true_bio[i] = 1
    
    precision = precision_score(true_bio, pred_bio, average='binary', zero_division=0)
    recall = recall_score(true_bio, pred_bio, average='binary', zero_division=0)
    f1 = f1_score(true_bio, pred_bio, average='binary', zero_division=0)
    
    accuracy = sum([1 if pred_bio[i] == true_bio[i] else 0 for i in range(text_length)]) / text_length
    
    return {
        'precision': round(precision, 3),
        'recall': round(recall, 3),
        'f1_score': round(f1, 3),
        'accuracy': round(accuracy, 3)
    }

def extract_entities(doc):
    """
    Extract entities from spaCy doc and format them
    """
    entities = []
    for ent in doc.ents:
        entities.append({
            'text': ent.text,
            'label': ent.label_,
            'start': ent.start_char,
            'end': ent.end_char
        })
    return entities

def parse_ground_truth(text, entities_json):
    """
    Parse ground truth entities from JSON format
    Expected format: [{"text": "entity", "label": "LABEL", "start": 0, "end": 5}, ...]
    """
    try:
        entities = json.loads(entities_json)
        text_length = len(text)
        valid_entities = []
        
        for ent in entities:
            if all(key in ent for key in ['text', 'label', 'start', 'end']):
                if 0 <= ent['start'] < text_length and 0 < ent['end'] <= text_length:
                    if text[ent['start']:ent['end']] == ent['text']:
                        valid_entities.append(ent)
        
        return valid_entities
    except json.JSONDecodeError:
        return []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/extract', methods=["GET", "POST"])
def extract():
    if request.method == 'POST':
        raw_text = request.form['rawtext']
        ground_truth_json = request.form.get('ground_truth', '[]')
        
        doc = nlp(raw_text)
        
        html = displacy.render(doc, style="ent")
        html = html.replace("\n\n", "\n")
        result = HTML_WRAPPER.format(html)
        
        predicted_entities = extract_entities(doc)
        
        ground_truth_entities = parse_ground_truth(raw_text, ground_truth_json)
        
        metrics = calculate_metrics(predicted_entities, ground_truth_entities, len(raw_text))
        
        return render_template(
            'result.html',
            rawtext=raw_text,
            result=result,
            metrics=metrics,
            predicted_entities=predicted_entities,
            ground_truth_entities=ground_truth_entities
        )
    
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
