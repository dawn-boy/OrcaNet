import os
import pandas as pd
from flask import Blueprint, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename
from .tasks import run_analysis_pipeline
import numpy as np
import plotly.express as px

bp = Blueprint('routes', __name__)


@bp.route('/')
def index():
    # ... (this function remains the same)
    return render_template('index.html')


@bp.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return "<p class='text-red-400 text-center'>No file part in the request.</p>", 400

    file = request.files['file']

    if file.filename == '':
        return "<p class='text-red-400 text-center'>No file selected.</p>", 400

    if file and file.filename.endswith('.json'):
        upload_folder = os.path.join(os.getcwd(), 'uploads')
        os.makedirs(upload_folder, exist_ok=True)

        filename = secure_filename(file.filename)
        json_path = os.path.join(upload_folder, filename)
        file.save(json_path)

        # Call the task with only the JSON file path
        task = run_analysis_pipeline.delay(json_path)
        return render_template(
            'partials/status.html',
            task_id=task.id,
            status='Initializing task...',
            state='PENDING',
            current_step=0,
            total_steps=3, # Matches the total_steps in your task
            completed_stages=[],
            logs='Waiting for task to start...'
        )
    return "<p class='text-red-400 text-center'>Invalid file type. Please upload a .json file.</p>", 400


# === THIS IS THE UPDATED FUNCTION ===
@bp.route('/task_status/<task_id>')
def task_status(task_id: str):
    task = run_analysis_pipeline.AsyncResult(task_id)
    context = {}  # A dictionary to hold all our template variables

    if task.state == 'SUCCESS':
        # If success, gather ALL data: final results AND progress history
        result_data = task.result
        all_contigs = result_data.get('contigs_data', [])

        context = {
            'task_id': task_id,
            'state': task.state,
            'status': 'Analysis Complete. See results below.',
            'completed_stages': task.info.get('completed_stages', []),
            'logs': task.info.get('logs', ''),
            'current_step': task.info.get('total_steps', 3),
            'total_steps': task.info.get('total_steps', 3),
            'result': result_data,
            'top_10_contigs': sorted(all_contigs, key=lambda x: x.get('novelty_score', 0), reverse=True)[:10],
            'contigs': all_contigs[0:25],  # First page for the table
            'page': 1,
            'total_pages': (len(all_contigs) + 24) // 25,
            'sort_by': 'novelty_score',
            'sort_order': 'desc',
            'plot_json': result_data.get('plot_json')
        }
    else:
        # If still running/pending/failed, just gather the progress data
        meta = task.info or {}
        context = {
            'task_id': task_id,
            'state': task.state,
            'status': meta.get('status', 'Initializing...'),
            'current_step': meta.get('current_step', 0),
            'total_steps': meta.get('total_steps', 3),
            'completed_stages': meta.get('completed_stages', []),
            'logs': meta.get('logs', 'Waiting for log output...')
        }

    # ALWAYS render status.html, passing whatever context we have.
    return render_template('partials/status.html', **context)


# --- NEW ROUTE for HTMX table updates ---
@bp.route('/results_table/<task_id>')
def results_table(task_id: str):
    task = run_analysis_pipeline.AsyncResult(task_id)
    all_contigs = task.result.get('contigs_data', [])

    # Get query parameters from the HTMX request
    page = request.args.get('page', 1, type=int)
    per_page = 25
    sort_by = request.args.get('sort_by', 'novelty_score', type=str)
    sort_order = request.args.get('sort_order', 'desc', type=str)

    # Sort the data
    reverse = (sort_order == 'desc')
    all_contigs.sort(key=lambda x: x.get(sort_by, 0), reverse=reverse)

    # Paginate the data
    start = (page - 1) * per_page
    end = start + per_page
    paginated_contigs = all_contigs[start:end]
    total_pages = (len(all_contigs) + per_page - 1) // per_page

    # Return just the table partial
    return render_template('partials/table.html',
                           task_id=task_id,
                           contigs=paginated_contigs,
                           page=page,
                           total_pages=total_pages,
                           sort_by=sort_by,
                           sort_order=sort_order)

@bp.route('/results_data/<task_id>/<path:filename>')
def serve_result_file(task_id, filename):
    directory = f"/orcanet/results_data/{task_id}"
    return send_from_directory(directory, filename)

@bp.route('/get_visualizations/<task_id>/<contig_id>')
def get_visualizations(task_id: str, contig_id: str):
    """
    Generates data for CGR image and Wavelet chart, then renders a partial.
    """
    # 1. Get the URL for the static CGR image we already created
    cgr_url = url_for('static', filename=f'cgr_images/cgr_{contig_id}.png')

    # 2. Generate a dummy wavelet chart on the fly
    # In your real app, this would be your actual wavelet transform data
    x_data = np.linspace(0, 10, 100)
    y_data = np.sin(x_data * int(contig_id[-1])) + np.random.normal(0, 0.1, 100)  # Wave depends on contig ID

    wave_fig = px.line(x=x_data, y=y_data, title=f"Morlet Wavelet (simulated) for {contig_id}")
    wave_fig.update_layout(template='plotly_dark', xaxis_title="Time", yaxis_title="Amplitude")
    wavelet_plot_json = wave_fig.to_json()

    # 3. Render a new partial template with all the data
    return render_template('partials/visualizations_panel.html',
                           contig_id=contig_id,
                           cgr_url=cgr_url,
                           wavelet_plot_json=wavelet_plot_json)


@bp.route('/contig_modal/<task_id>/<contig_id>')
def contig_modal_content(task_id: str, contig_id: str):
    task = run_analysis_pipeline.AsyncResult(task_id)
    if task.state != 'SUCCESS':
        return "<p>Task not complete or found.</p>"

    all_contigs = task.result.get('contigs_data', [])

    # Find the specific contig the user clicked on
    contig_data = next((c for c in all_contigs if c['contig_id'] == contig_id), None)

    if not contig_data:
        return f"<p>Contig {contig_id} not found.</p>"

    return render_template('partials/modal_content.html', contig=contig_data)