# app/ml/training_pipeline.py
"""
Training Pipeline — orchestrates full train/evaluate/save cycle.

Usage:
    pipeline = TrainingPipeline(user_id="abc-123")
    result   = pipeline.run()
    print(result['metrics'])
"""

from app.ml.dataset_builder import DatasetBuilder
from app.ml.model_trainer   import ModelTrainer
from typing import Dict, Any


class TrainingPipeline:

    def __init__(self, user_id: str):
        self.user_id = user_id

    def run(self) -> Dict[str, Any]:
        """
        Full training pipeline:
        1. Build dataset
        2. Train model
        3. Evaluate model
        4. Save model
        5. Return results

        Returns:
            Dict with metrics, feature importance, model path
        """
        print(f"\n{'='*50}")
        print(f"Training pipeline for user {self.user_id[:8]}")
        print(f"{'='*50}\n")

        # ── Step 1: Build dataset ───���──────────────────────────────────
        builder = DatasetBuilder(
            user_id=self.user_id,
            days_back=30
        )
        dataset = builder.build()

        # Check for errors
        if 'error' in dataset:
            return {
                'success': False,
                'error':   dataset['error'],
                'message': dataset.get('message', 'Dataset build failed')
            }

        X_train, X_test, y_train, y_test = dataset['splits']

        # Need at least 2 samples in test set
        if len(X_test) < 2:
            return {
                'success': False,
                'error':   'insufficient_test_data',
                'message': 'Need more sessions for reliable evaluation'
            }

        # ── Step 2: Train model ────────────────────────────────────────
        trainer = ModelTrainer()
        trainer.train(
            X_train=X_train,
            y_train=y_train,
            feature_names=dataset['feature_names']
        )

        # ── Step 3: Evaluate model ─────────────────────────────────────
        metrics = trainer.evaluate(X_test, y_test)

        # ── Step 4: Save model ─────────────────────────────────────────
        model_dir  = f"app/ml/models/{self.user_id[:8]}"
        model_path = trainer.save(model_dir=model_dir)

        # ── Step 5: Return results ─────────────────────────────────────
        feature_importance = trainer.get_feature_importance()

        print(f"\n{'='*50}")
        print(f"Training complete!")
        print(f"   Accuracy: {metrics['accuracy']:.1%}")
        print(f"{'='*50}\n")

        return {
            'success':            True,
            'metrics':            metrics,
            'feature_importance': feature_importance,
            'model_path':         model_path,
            'data_summary':       dataset['data_summary'],
            'label_balance':      dataset['label_balance'],
            'training_rows':      len(X_train),
            'test_rows':          len(X_test)
        }
