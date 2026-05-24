# PitWall AI Model Summary

## Data Summary
*   **Data Range**: 2018–2024
*   **Feature Rows**:
    *   Qualifying: 2,859 rows
    *   Race: 5,718 rows

## Models Trained
The backend currently supports the following tasks across two stages (`pre_weekend` and `post_qualifying`):
*   **Qualifying Position** (Regressor)
*   **Race Finish Position** (Regressor)
*   **Podium Finish** (Classifier)
*   **Top 10 Finish** (Classifier)

## Baseline vs. Advanced Models
*   **Baseline Models**: Powered by `RandomForest` and `LogisticRegression`. These models provide a stable floor for predictions and are trained quickly.
*   **Advanced Models**: Powered by `HistGradientBoosting`. These models use gradient boosting to capture non-linear interactions.

> **Warning**: The advanced models are currently in their early iterations. Due to the small dataset size and strong regularization required to prevent overfitting, **some naive baselines still outperform the advanced models on test sets.** The API will report these cases under the `warnings` array in the prediction response. Further feature engineering and hyperparameter tuning are required in future phases.
