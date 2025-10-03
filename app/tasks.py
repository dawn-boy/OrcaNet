import os
import time
import pandas as pd
from celery import shared_task
import plotly.graph_objects as go
import plotly.express as px
from scipy.spatial.distance import pdist, squareform # For distance matrix
from scipy.cluster.hierarchy import linkage, to_tree # For

def create_radar_chart(contig_data):
    """Creates a Plotly radar chart for a single contig's scores."""
    scores = {
        'Embedding': contig_data.get('embedding_score', 0),
        'Homology': contig_data.get('homology_score', 0),
        'Wavelet': contig_data.get('wavelet_score', 0),
        'Motif': contig_data.get('motif_score', 0),
        'Vision Uncertainty': contig_data.get('vision_uncertainty', 0)
    }

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=list(scores.values()),
        theta=list(scores.keys()),
        fill='toself',
        line=dict(color='cyan')
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 1], color='#888'),
            angularaxis=dict(color='#ccc')
        ),
        showlegend=False,
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=40, r=40, b=40, t=40)
    )
    return fig.to_json()

def get_newick(node, leaf_names):
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


@shared_task(bind=True)
def run_analysis_pipeline(self, json_filepath: str):
    completed_stages = []
    accumulated_log = ""
    pipeline_stages = [
        ("quality_control", "Stage 1: Quality Control"),
        ("metagenomic_assembly", "Stage 2: Metagenomic Assembly"),
        ("feature_extraction", "Stage 3: Feature Extraction"),
        ("novelty_scoring", "Stage 4: Novelty Scoring"),
        ("biological_context", "Stage 5: Biological Analysis"),
    ]
    total_stages = len(pipeline_stages)

    # Process at each stage
    for i, (stage_name, stage_title) in enumerate(pipeline_stages):
        current_step = i + 1

        log_output = f"--- Running {stage_title} ---\n"
        time.sleep(2)
        log_output += f"--- {stage_title} complete. ---\n\n"

        accumulated_log += log_output
        stage_result_data = {"status": "Completed successfully"} # just a placeholder, replace with actual data from the process

    # PLACEHOLDER VISUALS
        df = pd.read_json(json_filepath, orient='records')

        # STAGE ONE
        if stage_name == "quality_control":
            stage_result_data = {
                'high_quality_reads': 18500,
                'low_quality_reads': 5000,
            }

        # STAGE TWO
        if stage_name == "metagenomic_assembly":
            result_dir = f"/orcanet/results_data/{self.request.id}"
            os.makedirs(result_dir, exist_ok=True)

            fig = px.scatter_3d(
                df, x='UMAP_x', y='UMAP_y', z='UMAP_z', color='novelty_score',
                hover_data=['contig_id'], custom_data=['contig_id'],
                title="3D UMAP Projection of Assembled Contigs"
            )
            fig.update_layout(template='plotly_dark', margin=dict(l=0, r=0, b=0, t=40))
            plot_json = fig.to_json()

            try:
                tree_path = os.path.join(result_dir, "tree.nwk")
                if len(df) >= 2:
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

                    tree_root = to_tree(linked_tree)
                    newick_tree = get_newick(tree_root, df['contig_id'].tolist()) + ";"

                    with open(tree_path, "w") as f:
                        f.write(newick_tree)
                    print(f"Successfully wrote dynamic tree file to {tree_path}")

                    time.sleep(1)
            except Exception as e:
                print(f"ERROR: Could not write tree file. Reason: {e}")

            stage_result_data = {
                'plot_json': plot_json,
                'task_id': self.request.id
            }

        # STAGE FOUR
        if stage_name == "novelty_scoring":
            all_contigs = df.to_dict(orient='records')
            top_contig = sorted(all_contigs, key=lambda x: x.get('novelty_score', 0), reverse=True)[0]
            radar_plot_json = create_radar_chart(top_contig)
            stage_result_data = {
                "contig": top_contig,
                "plot_json": radar_plot_json
            }

        # STAGE FIVE
        elif stage_name == "biological_context":
            table_df = df.drop(columns=['UMAP_x', 'UMAP_y', 'UMAP_z'], errors='ignore')
            all_contigs = table_df.to_dict(orient='records')
            top_15_contigs = table_df.sort_values(by='novelty_score', ascending=False).head(15).to_dict(orient='records')
            stage_result_data = {
                'all_contigs': all_contigs,
                'top_15_contigs': top_15_contigs,
            }

        completed_stages.append({
            "name": stage_name,
            "title": stage_title,
            "data": stage_result_data,
        })

        # Stage a complete status update
        self.update_state(
            state="PROGRESS",
            meta={
                'status': f"Running {stage_title}...",
                'current_step': current_step,
                'total_stages': total_stages,
                'completed_stages': completed_stages,
                'logs': accumulated_log,
            })
        

    time.sleep(3)

    return {"status": "Complete", "final_meta": self.AsyncResult(self.request.id).info}
