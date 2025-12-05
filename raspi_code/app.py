# app.py - Standalone Web Viewer for CheckMe Database
"""
Simple Flask web interface to view CheckMe database records
Run this separately from main.py to monitor the system
"""

from flask import Flask, render_template, jsonify, request, send_file
import sqlite3
import json
import os
from datetime import datetime

app = Flask(__name__)

# Database configuration
DB_PATH = "database/checkme.db"

def get_db_connection():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================
# DASHBOARD ROUTES
# ============================================================

@app.route('/')
def dashboard():
    """Main dashboard page."""
    return render_template('dashboard.html')


@app.route('/api/stats')
def get_stats():
    """Get system statistics."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Answer keys stats
        cursor.execute('SELECT COUNT(*) as total FROM answer_keys')
        total_keys = cursor.fetchone()['total']
        
        # Answer sheets stats
        cursor.execute('SELECT COUNT(*) as total FROM answer_sheets')
        total_sheets = cursor.fetchone()['total']
        
        cursor.execute('SELECT COUNT(*) as processed FROM answer_sheets WHERE student_id IS NOT NULL')
        processed_sheets = cursor.fetchone()['processed']
        
        cursor.execute('SELECT COUNT(*) as unprocessed FROM answer_sheets WHERE student_id IS NULL')
        unprocessed_sheets = cursor.fetchone()['unprocessed']
        
        cursor.execute('SELECT COUNT(*) as final FROM answer_sheets WHERE is_final_score = 1')
        final_scores = cursor.fetchone()['final']
        
        cursor.execute('SELECT COUNT(*) as needs_manual FROM answer_sheets WHERE is_final_score = 0 AND student_id IS NOT NULL')
        needs_manual = cursor.fetchone()['needs_manual']
        
        # Average score
        cursor.execute('SELECT AVG(score) as avg_score FROM answer_sheets WHERE score > 0')
        avg_result = cursor.fetchone()
        avg_score = round(avg_result['avg_score'], 2) if avg_result['avg_score'] else 0
        
        conn.close()
        
        return jsonify({
            'status': 'success',
            'data': {
                'answer_keys': total_keys,
                'total_sheets': total_sheets,
                'processed': processed_sheets,
                'unprocessed': unprocessed_sheets,
                'final_scores': final_scores,
                'needs_manual': needs_manual,
                'avg_score': avg_score
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ============================================================
# ANSWER KEYS ROUTES
# ============================================================

@app.route('/answer-keys')
def answer_keys_page():
    """Answer keys listing page."""
    return render_template('answer_keys.html')


@app.route('/api/answer-keys')
def get_answer_keys():
    """Get all answer keys."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                id,
                assessment_uid,
                number_of_pages,
                json_path,
                img_path,
                has_essay,
                saved_at
            FROM answer_keys
            ORDER BY saved_at DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        keys = []
        for row in rows:
            keys.append({
                'id': row['id'],
                'assessment_uid': row['assessment_uid'],
                'number_of_pages': row['number_of_pages'],
                'json_path': row['json_path'],
                'img_path': row['img_path'],
                'has_essay': bool(row['has_essay']),
                'saved_at': row['saved_at']
            })
        
        return jsonify({'status': 'success', 'data': keys})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/answer-keys/<int:key_id>')
def get_answer_key_detail(key_id):
    """Get answer key details with JSON content."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM answer_keys WHERE id = ?', (key_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({'status': 'error', 'message': 'Answer key not found'}), 404
        
        key_data = {
            'id': row['id'],
            'assessment_uid': row['assessment_uid'],
            'number_of_pages': row['number_of_pages'],
            'json_path': row['json_path'],
            'img_path': row['img_path'],
            'has_essay': bool(row['has_essay']),
            'saved_at': row['saved_at']
        }
        
        # Load JSON content if exists
        if os.path.exists(row['json_path']):
            with open(row['json_path'], 'r') as f:
                key_data['answers'] = json.load(f)
        
        return jsonify({'status': 'success', 'data': key_data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ============================================================
# ANSWER SHEETS ROUTES
# ============================================================

@app.route('/answer-sheets')
def answer_sheets_page():
    """Answer sheets listing page."""
    return render_template('answer_sheets.html')


@app.route('/api/answer-sheets')
def get_answer_sheets():
    """Get all answer sheets with optional filters."""
    try:
        assessment_uid = request.args.get('assessment_uid')
        status = request.args.get('status')  # 'processed', 'unprocessed', 'needs_manual'
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT 
                id,
                assessment_uid,
                student_id,
                number_of_pages,
                json_file_name,
                json_path,
                img_path,
                score,
                is_final_score,
                is_image_uploaded,
                saved_at,
                image_uploaded_at
            FROM answer_sheets
            WHERE 1=1
        '''
        params = []
        
        if assessment_uid:
            query += ' AND assessment_uid = ?'
            params.append(assessment_uid)
        
        if status == 'processed':
            query += ' AND student_id IS NOT NULL'
        elif status == 'unprocessed':
            query += ' AND student_id IS NULL'
        elif status == 'needs_manual':
            query += ' AND is_final_score = 0 AND student_id IS NOT NULL'
        
        query += ' ORDER BY saved_at DESC'
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        sheets = []
        for row in rows:
            sheets.append({
                'id': row['id'],
                'assessment_uid': row['assessment_uid'],
                'student_id': row['student_id'],
                'number_of_pages': row['number_of_pages'],
                'json_file_name': row['json_file_name'],
                'json_path': row['json_path'],
                'img_path': row['img_path'],
                'score': row['score'],
                'is_final_score': bool(row['is_final_score']),
                'is_image_uploaded': bool(row['is_image_uploaded']),
                'saved_at': row['saved_at'],
                'image_uploaded_at': row['image_uploaded_at']
            })
        
        return jsonify({'status': 'success', 'data': sheets})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/answer-sheets/<int:sheet_id>')
def get_answer_sheet_detail(sheet_id):
    """Get answer sheet details with graded results."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM answer_sheets WHERE id = ?', (sheet_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({'status': 'error', 'message': 'Answer sheet not found'}), 404
        
        sheet_data = {
            'id': row['id'],
            'assessment_uid': row['assessment_uid'],
            'student_id': row['student_id'],
            'number_of_pages': row['number_of_pages'],
            'json_file_name': row['json_file_name'],
            'json_path': row['json_path'],
            'img_path': row['img_path'],
            'score': row['score'],
            'is_final_score': bool(row['is_final_score']),
            'is_image_uploaded': bool(row['is_image_uploaded']),
            'saved_at': row['saved_at'],
            'image_uploaded_at': row['image_uploaded_at']
        }
        
        # Load graded JSON content if exists
        if os.path.exists(row['json_path']):
            with open(row['json_path'], 'r') as f:
                sheet_data['graded_result'] = json.load(f)
        
        return jsonify({'status': 'success', 'data': sheet_data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/answer-sheets/<int:sheet_id>/update-score', methods=['POST'])
def update_manual_score(sheet_id):
    """Update score manually (for essay grading)."""
    try:
        data = request.get_json()
        new_score = data.get('score')
        
        if new_score is None:
            return jsonify({'status': 'error', 'message': 'Score is required'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE answer_sheets
            SET score = ?, is_final_score = 1
            WHERE id = ?
        ''', (new_score, sheet_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'status': 'success', 'message': 'Score updated successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ============================================================
# IMAGE VIEWER ROUTE
# ============================================================

@app.route('/api/image')
def view_image():
    """Serve image files."""
    img_path = request.args.get('path')
    
    if not img_path or not os.path.exists(img_path):
        return "Image not found", 404
    
    return send_file(img_path, mimetype='image/jpeg')


# ============================================================
# RUN SERVER
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("CheckMe Web Viewer Starting...")
    print("=" * 60)
    print("📊 Dashboard: http://localhost:5050")
    print("🔑 Answer Keys: http://localhost:5050/answer-keys")
    print("📝 Answer Sheets: http://localhost:5050/answer-sheets")
    print("=" * 60)
    
    app.run(
        host='0.0.0.0',
        port=5050,
        debug=True
    )