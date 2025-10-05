import os

from flask import Blueprint, render_template, request, Response
from werkzeug.utils import secure_filename

from . import tasks

bp = Blueprint('routes', __name__)

@bp.route('/')
def index():
    return render_template('upload_page.html')
    #return render_template('analysis_page.html', task_id="548149c8-345c-41db-b4ec-6968837564c5")


@bp.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return "Error: No file part in the request.", 400

    file = request.files['file']

    if file.filename == '':
        return "Error: No file selected.", 400

    upload_folder = '/orcanet/uploads'
    os.makedirs(upload_folder, exist_ok=True)
    filename = secure_filename(file.filename)
    json_path = os.path.join(upload_folder, filename)
    file.save(json_path)
    print("HIIII", json_path)

    task = tasks.run_analysis_pipeline.delay(json_path)

    return render_template('analysis_page.html', task_id=task.id)
    #if request.headers.get('HX-Request'):
    #    return render_template('partials/analysis_content.html', task_id=task.id)  # only content
    #else:
        #return render_template('analysis_page.html', task_id=task.id)  # full page with base


@bp.route('/task_status/<task_id>')
def task_status(task_id: str):
    task = tasks.run_analysis_pipeline.AsyncResult(task_id)
    response_html = ""

    if task.info:
        meta = task.info
        active_stage = meta.get('active_stage')

        # Check if the active stage is Quality Control
        if active_stage == 'quality_control':
            # Render the QC card's content, passing the stage_data if it exists
            card_html = render_template(
                'partials/quality_control_card.html',
                stage_data=meta.get('stage_data')
            )
            # Wrap it in an OOB swap targeting our card's div
            response_html += f'<div id="quality-control-card" hx-swap-oob="innerHTML">{card_html}</div>'

    # This stops the polling when the task is done
    if task.state in ['SUCCESS', 'FAILURE']:
        response_html += '<div hx-swap-oob="true" id="analysis-container"></div>'

    return Response(response_html)