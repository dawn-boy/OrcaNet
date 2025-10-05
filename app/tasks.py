import time
from celery import shared_task
import os
import pandas as pd
import random

from flask import render_template



@shared_task(bind=True)
def run_analysis_pipeline(self, json_filepath: str):
    df = pd.read_json(json_filepath, orient='records')
    total_contigs = len(df)

    pipeline_stages = [
        ("quality_control", "Stage 1: Quality Control"),
    ]
    total_stages = len(pipeline_stages)

    current_step = 1
    self.update_state(state='PROGRESS', meta={
        'current_step': current_step,
        'total_stages': total_stages,
        'active_stage': 'quality_control'
    })
    time.sleep(2)  # Simulate the 2-second progress bar

    high_quality_count = random.randint(int(total_contigs * 0.8), total_contigs)
    low_quality_count = total_contigs - high_quality_count

    self.update_state(state='PROGRESS', meta={
        'current_step': current_step,
        'total_stages': total_stages,
        'active_stage': 'quality_control',  # Still the active stage
        'stage_data': {  # The final data for this card
            'high_quality_reads': high_quality_count,
            'low_quality_reads': low_quality_count
        }
    })

    time.sleep(3)

    return {"status": "Complete"}
