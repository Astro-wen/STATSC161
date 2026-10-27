# Presentation notes

## 1 Question and data

Our question is how well wallet trading characteristics predict average purchase price, and whether gradient boosting improves on linear regression. The dataset contains 55,952 wallets, with one row per wallet. The target is the volume weighted price of shares each wallet bought. The histogram summarizes training wallets and uses five broader price bins for readability. We retain all wallets and completely exclude the confirmed flag. This cohort comes from five selected event groups, so we describe the wallets in this dataset. A higher or lower purchase price does not itself tell us whether the wallet made a profit.

Sources: wallet_analysis/data/wallet_features.csv; the opening data dictionary in the course insider_demo.ipynb; tables/target_histogram_training.csv. The native slide histogram aggregates each five adjacent bins from Figure 01. No target values from the final test set enter this chart.

## 2 Approach

We reserve twenty percent of the wallets for final evaluation, using one fixed random split. This gives 44,761 training wallets and 11,191 test wallets. Every method receives exactly the same test wallets. Five-fold validation happens entirely inside training. We compare a mean baseline, an additive linear regression, and histogram gradient boosting, which can capture nonlinear patterns and interactions. The inputs are trade count, market count, observed activity span, concentration, total spending, and largest purchase. Five skewed predictors use log of one plus the value. Linear regression also standardizes its inputs using training statistics. We select boosting settings from a small six-configuration grid using validation MAE. The test set stays outside model selection.

Sources: code/analyze_wallet_prices.py; tables/wallet_split.csv; tables/cv_grid_full.csv; https://scikit-learn.org/1.7/modules/cross_validation.html; https://scikit-learn.org/1.7/modules/generated/sklearn.ensemble.HistGradientBoostingRegressor.html. Fixed settings: 250 iterations, learning rate 0.06, minimum leaf size 30, early stopping disabled. Grid: maximum leaves 7, 15, 31 and L2 regularization 0 or 1. Both learned models fit squared error. Selected full specification: 31 leaves and L2=1.

## 3 Results

On the held out wallets, the mean baseline has an average absolute error of 22.14 cents per share. Linear regression reduces this to 19.78 cents, and gradient boosting reduces it further to 16.74 cents. That is a 15.4 percent improvement over linear regression. The absolute difference is 3.04 cents, with a paired wallet-bootstrap interval from 2.86 to 3.23 cents. Boosting also has a higher R squared, about 0.368 compared with 0.197 for linear regression. The model comparison is consistent across MAE, RMSE, and R squared. These intervals describe uncertainty on the test wallets conditional on our fitted models. They assume independent wallets, which may be imperfect because wallets can trade in common markets.

Sources: tables/primary_model_metrics.csv; tables/paired_bootstrap_comparisons.csv; Figure 06. The editable chart preserves the point estimates. Individual-model MAE intervals and RMSE values remain in the comprehensive report. R² compares test squared error with variation around the test mean. No predictions are clipped in the main evaluation.

## 4 Interpretation

To interpret the flexible model, we shuffle one predictor at a time and measure the increase in test MAE. Trade count produces the largest increase, about 6.32 cents. Spending, largest purchase, and number of markets also contribute. This measures reliance by the fitted model, and it does not tell us whether an input raises or lowers price. Correlated predictors complicate attribution. In a sensitivity analysis, removing spending and largest purchase increases boosting error from 16.74 to 19.97 cents, so the monetary summaries add information. They are computed from the same observed trades as the target. The analysis therefore predicts differences across wallets within the observed history. Market choice and timing may explain part of those differences. We cannot infer profit, trading skill, future forecasting accuracy, or causal effects from this table.

Sources: tables/permutation_importance_test.csv; tables/all_model_metrics.csv; Figure 12 and Figure 14; https://scikit-learn.org/1.7/modules/permutation_importance.html. Native chart values are mean error increases over 20 shuffles. Shuffle standard deviations are in the comprehensive report and are not causal confidence intervals. The activity-only boosting comparison uses its own training-only search with the same grid. The confirmed flag is absent from the entire analysis.