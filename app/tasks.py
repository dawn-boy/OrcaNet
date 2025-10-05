import time
from celery import shared_task
import os
import pandas as pd
import plotly.express as px
from celery.states import state
from scipy.spatial.distance import pdist, squareform # For distance matrix
from scipy.cluster.hierarchy import linkage, to_tree # For clustering
import json # <-- Import the json library


@shared_task(bind=True)
def run_analysis_pipeline(self, json_filepath: str):
    filename = os.path.basename(json_filepath)
    result_dir = f"/orcanet/results_data/{self.request.id}"
    os.makedirs(result_dir, exist_ok=True)
    total_steps = 3
    input_fasta_path = json_filepath.replace('.json', '.fasta')

    completed_stages = []
    accumulated_log = ""

    try:
        # === STAGE 1: fastp ===
        print("Starting Stage 1: fastp...")
        time.sleep(3)  # Simulate work

        # Capture results for this stage
        log_output_1 = f"fastp --in1 {input_fasta_path}\n" \
                       "Simulated fastp run complete.\n" \
                       "Total reads: 20000, Reads passed filter: 18500\n"
        accumulated_log += log_output_1

        high_quality_reads = 18500
        low_quality_reads = 20000 - 18500
        completed_stages.append({
            "name": "fastp_qc", "title": "Stage 1: Quality Control (fastp)",
            "data": {'high_quality_reads': high_quality_reads, 'low_quality_reads': low_quality_reads}
        })

        # Send ONE complete update AFTER stage 1 is done
        self.update_state(state='PROGRESS', meta={
            'status': f'Step 1/{total_steps}: fastp QC Complete.', 'current_step': 1, 'total_steps': total_steps,
            'completed_stages': completed_stages, 'logs': accumulated_log
        })

        # === STAGE 2: kraken2 ===
        print("Starting Stage 2: kraken2...")
        time.sleep(3)  # Simulate work

        log_output_2 = "\nkraken2 run complete.\nRemoved 500 contaminant reads.\n"
        accumulated_log += log_output_2
        completed_stages.append({
            "name": "kraken2_filter", "title": "Stage 2: Contamination Filtering (kraken2)",
            "data": {"contaminants_removed": 500}
        })

        # Send ONE complete update AFTER stage 2 is done
        self.update_state(state='PROGRESS', meta={
            'status': f'Step 2/{total_steps}: Contamination filtering complete.', 'current_step': 2,
            'total_steps': total_steps,
            'completed_stages': completed_stages, 'logs': accumulated_log
        })

        # === STAGE 3: Feature Extraction ===
        print("Starting Stage 3: Feature Extraction...")
        time.sleep(3)  # Simulate work

        log_output_3 = "\nFeature extraction complete.\n"
        accumulated_log += log_output_3
        completed_stages.append({
            "name": "feature_extraction", "title": "Stage 3: Feature Extraction",
            "data": {"features_extracted": 12345}
        })

        # Send ONE complete update AFTER stage 3 is done
        self.update_state(state='PROGRESS', meta={
            'status': f'Step 3/{total_steps}: Feature extraction complete.', 'current_step': 3,
            'total_steps': total_steps,
            'completed_stages': completed_stages, 'logs': accumulated_log
        })
        time.sleep(1)  # Final pause before returning success
    except Exception as e:
        print(f"ERROR: {e}")
        return {'status': 'Error', 'result': f'Error during analysis: {e}'}

    df = pd.read_json(json_filepath, orient='records')

    try:
        tree_path = os.path.join(result_dir, "tree.nwk")
        if len(df) >= 2:
            # --- This part is the same ---
            features_for_tree = ['UMAP_x', 'UMAP_y', 'UMAP_z']
            available_features = [f for f in features_for_tree if f in df.columns]
            if available_features:
                X = df[available_features].values
            elif 'novelty_score' in df.columns:
                X = df[['novelty_score']].values
            else:
                raise ValueError("No suitable features found for tree generation.")

            distance_matrix = pdist(X, metric='euclidean')
            linked_tree = linkage(distance_matrix, method='average')

            # --- This part is updated ---
            # Convert the linkage to a ClusterNode object which is easier to parse
            tree_root = to_tree(linked_tree)
            # Call our new, corrected get_newick function
            newick_tree = get_newick(tree_root, df['contig_id'].tolist()) + ";"

            with open(tree_path, "w") as f:
                f.write(newick_tree)
            print(f"Successfully wrote dynamic tree file to {tree_path}")
        # ... (rest of the try/except is the same)
    except Exception as e:
        print(f"ERROR: Could not write tree file. Reason: {e}")

    # --- Generate table and plot (same as before) ---
    table_df = df.drop(columns=['UMAP_x', 'UMAP_y', 'UMAP_z'], errors='ignore')

    contigs_data = table_df.to_dict(orient='records')

    fig = px.scatter_3d(
        df, x='UMAP_x', y='UMAP_y', z='UMAP_z', color='novelty_score',
        hover_data=['contig_id'], custom_data=['contig_id'],
        title="3D UMAP Projection of eDNA Bins",
        color_continuous_scale=px.colors.sequential.Viridis
    )
    fig.update_layout(template='plotly_dark', margin=dict(l=0, r=0, b=0, t=40))
    plot_json = fig.to_json()


    self.update_state(state='SUCCESS', meta={'status': 'Complete!', 'result': f'Analysis of {filename} is finished.',
                                             'contigs_data': contigs_data, 'plot_json': plot_json, 'task_id': self.request.id})
    return {
        'status': 'Complete!',
        'result': f'Analysis of {filename} is finished.',
        'contigs_data': contigs_data,
        'plot_json': plot_json,
        'task_id': self.request.id  # Pass the task ID so we can build file URLs
    }


def get_newick(node, leaf_names):
    """
    Recursively convert a scipy.cluster.hierarchy.ClusterNode to a valid Newick string.
    """
    if node.is_leaf():
        # If it's a leaf, return its name
        return leaf_names[node.id]
    else:
        # If it's a branch, recursively call for its children
        left_branch = get_newick(node.left, leaf_names)
        right_branch = get_newick(node.right, leaf_names)

        # Branch length is the difference in height between parent and child
        left_len = node.dist - node.left.dist
        right_len = node.dist - node.right.dist

        # Return the formatted Newick string for this node
        return f"({left_branch}:{left_len:.6f},{right_branch}:{right_len:.6f})"
