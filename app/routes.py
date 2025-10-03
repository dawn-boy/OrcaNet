import os
from flask import Blueprint, render_template, request, Response, send_from_directory
from werkzeug.utils import secure_filename
from . import tasks

bp = Blueprint('routes', __name__)

# Root route
@bp.route('/')
def index():
    return render_template('index.html')

# Upload route [post]
@bp.route('/upload', methods=['POST'])
def upload_file():
    # pre-checks before saving the file
    if 'file' not in request.files:
        return "<p class='text-red-400 text-center'>No file part in the request.</p>", 400
    file = request.files['file']
    if file.filename == '' or not file.filename.endswith('.json'):
        return "<p class='text-red-400 text-center'>Please select a valid .json file.</p>", 400

    # save the file
    upload_folder = '/orcanet/uploads'
    os.makedirs(upload_folder, exist_ok=True)
    filename = secure_filename(file.filename)
    json_path = os.path.join(upload_folder, filename)
    file.save(json_path)

    # Start the bg task
    task = tasks.run_analysis_pipeline.delay(json_path)

    # show the progress screen to the user
    return render_template(
        'partials/status.html',
        task_id=task.id,
    )

@bp.route('/task_status/<task_id>')
def task_status(task_id: str):
    client_stage_count = request.args.get('client_stage_count', 0, type=int)
    task = tasks.run_analysis_pipeline.AsyncResult(task_id)

    if not task.info:
        return render_template(
            'partials/progress_updater.html',
            task_id=task_id,
            status='Initializing...', percent=0, client_stage_count=0
        )

    meta = task.info
    completed_stages = meta.get('completed_stages', [])
    server_stage_count = len(completed_stages)

    new_stages = completed_stages[client_stage_count:]
    oob_response = ""
    for stage in new_stages:
        card_html = render_template('partials/stage_card.html', stage=stage, task_id=task_id)
        oob_response += f'<div hx-swap-oob="afterbegin:#stacked-results">{card_html}</div>'

    progress_updater_html = render_template(
        'partials/progress_updater.html',
        task_id=task_id,
        status=meta.get('status', ''),
        percent=(meta.get('current_step', 0) / meta.get('total_stages', 1) * 100),
        client_stage_count=server_stage_count,
        state=task.state,
        logs=meta.get('logs', '')
    )

    if task.state == 'SUCCESS':
        progress_updater_html = render_template('partials/progress_updater.html', status="Analysis Complete!", percent=100, client_stage_count=server_stage_count, state=task.state)

    return Response(oob_response + progress_updater_html)


@bp.route('/contig_modal/<task_id>/<contig_id>')
def contig_modal_content(task_id: str, contig_id: str):
    task = tasks.run_analysis_pipeline.AsyncResult(task_id)
    if task.state != 'SUCCESS':
        return "<p class='p-6'>Task not complete or found.</p>"

    # The result is now in task.result['final_meta']
    all_contigs = task.result.get('final_meta', {}).get('completed_stages', [])[-1].get('data', {}).get('all_contigs',
                                                                                                        [])

    if not all_contigs:
        return "<p class='p-6'>Contig data not found in task result.</p>"

    # Find the specific contig the user clicked on
    contig_data = next((c for c in all_contigs if c['contig_id'] == contig_id), None)

    if not contig_data:
        return f"<p class='p-6'>Contig {contig_id} not found.</p>"

    return render_template('partials/modal_content.html', contig=contig_data)

@bp.route('/results_table/<task_id>')
def results_table(task_id: str):
    task = tasks.run_analysis_pipeline.AsyncResult(task_id)
    if task.state != 'SUCCESS':
        return ""

    all_contigs = task.result.get('final_meta', {}).get('completed_stages', [])[-1].get('data', {}).get('all_contigs',
                                                                                                        [])

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    sort_by = request.args.get('sort_by', 'novelty_score', type=str)
    sort_order = request.args.get('sort_order', 'desc', type=str)

    if sort_by == 'contig_id':
        sort_key = lambda x: int(x['contig_id'].split('_')[1])
    else:
        sort_key = lambda x: x.get(sort_by, 0)

    reverse = (sort_order == 'desc')
    all_contigs.sort(key=sort_key, reverse=reverse)

    start = (page - 1) * per_page
    end = start + per_page
    paginated_contigs = all_contigs[start:end]
    total_pages = (len(all_contigs) + per_page - 1)

    return render_template('partials/table.html',
                           task_id=task_id,
                           contigs=paginated_contigs,
                           page=page,
                           per_page=per_page,
                           total_pages=total_pages,
                           sort_by=sort_by,
                           sort_order=sort_order)


@bp.route('/update_radar/<task_id>/<contig_id>')
def update_radar(task_id: str, contig_id: str):
    task = tasks.run_analysis_pipeline.AsyncResult(task_id)
    if task.state != 'SUCCESS':
        return "<p>Task not complete or found.</p>"

    all_contigs = task.result.get('final_meta', {}).get('completed_stages', [])[-1].get('data', {}).get('all_contigs',
                                                                                                        [])
    contig_data = next((c for c in all_contigs if c['contig_id'] == contig_id), None)

    if not contig_data:
        return f"<p>Contig {contig_id} not found.</p>"

    radar_plot_json = tasks.create_radar_chart(contig_data)
    return render_template('partials/radar_card_content.html',
                           contig=contig_data,
                           plot_json=radar_plot_json)

@bp.route('/results_data/<task_id>/<path:filename>')
def serve_result_file(task_id, filename):
    directory = f"/orcanet/results_data/{task_id}"
    return send_from_directory(directory, filename)