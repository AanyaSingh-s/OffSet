# Results (held-out test users)

## Overall, extended tier

| System                          |   precision |   recall |    f1 |   fpr |   fnr |   roc_auc |   pr_auc |   tp |   fp |   fn |    tn |
|:--------------------------------|------------:|---------:|------:|------:|------:|----------:|---------:|-----:|-----:|-----:|------:|
| A. Rules only                   |       0.732 |    0.313 | 0.439 | 0.005 | 0.687 |   nan     |  nan     |  569 |  208 | 1248 | 38182 |
| B. ML only: logistic_regression |       0.54  |    0.647 | 0.588 | 0.026 | 0.353 |     0.93  |    0.676 | 1175 | 1002 |  642 | 37388 |
| C. Hybrid: logistic_regression  |       0.525 |    0.658 | 0.584 | 0.028 | 0.342 |     0.935 |    0.68  | 1195 | 1081 |  622 | 37309 |
| B. ML only: random_forest       |       0.592 |    0.84  | 0.694 | 0.027 | 0.16  |     0.979 |    0.831 | 1526 | 1052 |  291 | 37338 |
| C. Hybrid: random_forest        |       0.571 |    0.835 | 0.678 | 0.03  | 0.165 |     0.979 |    0.831 | 1518 | 1142 |  299 | 37248 |
| B. ML only: isolation_forest    |       0.453 |    0.372 | 0.408 | 0.021 | 0.628 |     0.871 |    0.422 |  676 |  817 | 1141 | 37573 |
| C. Hybrid: isolation_forest     |       0.456 |    0.424 | 0.44  | 0.024 | 0.576 |     0.876 |    0.435 |  771 |  919 | 1046 | 37471 |

95% user-bootstrap intervals, extended tier

| system                          |   precision_lo |   precision_hi |   recall_lo |   recall_hi |   f1_lo |   f1_hi |   fpr_lo |   fpr_hi |
|:--------------------------------|---------------:|---------------:|------------:|------------:|--------:|--------:|---------:|---------:|
| A. Rules only                   |          0.647 |          0.803 |       0.269 |       0.355 |   0.388 |   0.482 |    0.004 |    0.007 |
| B. ML only: logistic_regression |          0.485 |          0.586 |       0.601 |       0.682 |   0.543 |   0.625 |    0.024 |    0.029 |
| C. Hybrid: logistic_regression  |          0.468 |          0.571 |       0.613 |       0.693 |   0.539 |   0.62  |    0.025 |    0.031 |
| B. ML only: random_forest       |          0.547 |          0.627 |       0.801 |       0.872 |   0.658 |   0.723 |    0.025 |    0.03  |
| C. Hybrid: random_forest        |          0.524 |          0.61  |       0.798 |       0.867 |   0.642 |   0.709 |    0.027 |    0.033 |
| B. ML only: isolation_forest    |          0.389 |          0.509 |       0.32  |       0.415 |   0.355 |   0.45  |    0.019 |    0.024 |
| C. Hybrid: isolation_forest     |          0.394 |          0.513 |       0.379 |       0.467 |   0.389 |   0.479 |    0.021 |    0.027 |

## ML on rule-passing rows only, extended tier

| model               |   residual_rows |   residual_fraud |   tp |   fp |   fn |    tn |   precision |   recall |    f1 |   fpr |   fnr |   accuracy |   roc_auc |   pr_auc |
|:--------------------|----------------:|-----------------:|-----:|-----:|-----:|------:|------------:|---------:|------:|------:|------:|-----------:|----------:|---------:|
| logistic_regression |           39430 |             1248 |  626 |  873 |  622 | 37309 |       0.418 |    0.502 | 0.456 | 0.023 | 0.498 |      0.962 |     0.909 |    0.469 |
| random_forest       |           39430 |             1248 |  949 |  934 |  299 | 37248 |       0.504 |    0.76  | 0.606 | 0.024 | 0.24  |      0.969 |     0.972 |    0.718 |
| isolation_forest    |           39430 |             1248 |  202 |  711 | 1046 | 37471 |       0.221 |    0.162 | 0.187 | 0.019 | 0.838 |      0.955 |     0.826 |    0.147 |

## Per-scenario recall, extended tier

| scenario                       |   ('recall', 'hybrid_random_forest') |   ('recall', 'ml_random_forest') |   ('recall', 'rules_only') |   ('attack_recall', 'hybrid_random_forest') |   ('attack_recall', 'ml_random_forest') |   ('attack_recall', 'rules_only') |
|:-------------------------------|-------------------------------------:|---------------------------------:|---------------------------:|--------------------------------------------:|----------------------------------------:|----------------------------------:|
| combined                       |                                 0.93 |                             0.91 |                       0.26 |                                        1    |                                    1    |                              0.38 |
| cumulative_offline_spend       |                                 0.7  |                             0.72 |                       0.09 |                                        0.94 |                                    0.94 |                              0.26 |
| device_change                  |                                 0.82 |                             0.87 |                       0.04 |                                        0.87 |                                    0.94 |                              0.06 |
| double_spend                   |                                 1    |                             1    |                       1    |                                        1    |                                    1    |                              1    |
| large_amount                   |                                 0.88 |                             0.88 |                       0    |                                        0.88 |                                    0.88 |                              0    |
| long_offline_suspicious        |                                 0.99 |                             0.98 |                       0.42 |                                        1    |                                    1    |                              0.45 |
| new_beneficiary_unusual_amount |                                 0.98 |                             0.98 |                       0.06 |                                        1    |                                    1    |                              0.05 |
| replay_duplicate               |                                 1    |                             0.98 |                       1    |                                        1    |                                    0.98 |                              1    |
| rollback                       |                                 0.79 |                             0.8  |                       0.31 |                                        0.84 |                                    0.86 |                              0.44 |
| velocity_burst                 |                                 0.85 |                             0.85 |                       0.43 |                                        0.94 |                                    0.92 |                              0.68 |

## Unseen-scenario recall (hybrid, RF), extended tier

| scenario                       |   seen |   unseen |   rules |
|:-------------------------------|-------:|---------:|--------:|
| combined                       |   0.93 |     0.87 |    0.26 |
| cumulative_offline_spend       |   0.7  |     0.24 |    0.09 |
| device_change                  |   0.82 |     0.58 |    0.04 |
| double_spend                   |   1    |     1    |    1    |
| large_amount                   |   0.88 |     0.4  |    0    |
| long_offline_suspicious        |   0.99 |     0.78 |    0.42 |
| new_beneficiary_unusual_amount |   0.98 |     0.81 |    0.06 |
| replay_duplicate               |   1    |     1    |    1    |
| rollback                       |   0.79 |     0.54 |    0.31 |
| velocity_burst                 |   0.85 |     0.49 |    0.43 |

## Overall, native tier

| System                          |   precision |   recall |    f1 |   fpr |   fnr |   roc_auc |   pr_auc |   tp |   fp |   fn |    tn |
|:--------------------------------|------------:|---------:|------:|------:|------:|----------:|---------:|-----:|-----:|-----:|------:|
| A. Rules only                   |       0.342 |    0.059 | 0.101 | 0.005 | 0.941 |   nan     |  nan     |  108 |  208 | 1709 | 38182 |
| B. ML only: logistic_regression |       0.515 |    0.581 | 0.546 | 0.026 | 0.419 |     0.916 |    0.608 | 1056 |  995 |  761 | 37395 |
| C. Hybrid: logistic_regression  |       0.498 |    0.596 | 0.542 | 0.028 | 0.404 |     0.918 |    0.61  | 1083 | 1093 |  734 | 37297 |
| B. ML only: random_forest       |       0.572 |    0.768 | 0.655 | 0.027 | 0.232 |     0.962 |    0.769 | 1395 | 1045 |  422 | 37345 |
| C. Hybrid: random_forest        |       0.561 |    0.765 | 0.647 | 0.028 | 0.235 |     0.963 |    0.77  | 1390 | 1089 |  427 | 37301 |
| B. ML only: isolation_forest    |       0.429 |    0.34  | 0.38  | 0.021 | 0.66  |     0.848 |    0.395 |  618 |  821 | 1199 | 37569 |
| C. Hybrid: isolation_forest     |       0.426 |    0.371 | 0.396 | 0.024 | 0.629 |     0.853 |    0.404 |  674 |  909 | 1143 | 37481 |

95% user-bootstrap intervals, native tier

| system                          |   precision_lo |   precision_hi |   recall_lo |   recall_hi |   f1_lo |   f1_hi |   fpr_lo |   fpr_hi |
|:--------------------------------|---------------:|---------------:|------------:|------------:|--------:|--------:|---------:|---------:|
| A. Rules only                   |          0.268 |          0.429 |       0.044 |       0.08  |   0.078 |   0.134 |    0.004 |    0.007 |
| B. ML only: logistic_regression |          0.46  |          0.561 |       0.53  |       0.622 |   0.494 |   0.582 |    0.023 |    0.028 |
| C. Hybrid: logistic_regression  |          0.443 |          0.543 |       0.55  |       0.635 |   0.495 |   0.577 |    0.025 |    0.031 |
| B. ML only: random_forest       |          0.525 |          0.611 |       0.724 |       0.801 |   0.616 |   0.686 |    0.025 |    0.03  |
| C. Hybrid: random_forest        |          0.51  |          0.605 |       0.722 |       0.798 |   0.606 |   0.679 |    0.026 |    0.031 |
| B. ML only: isolation_forest    |          0.36  |          0.486 |       0.279 |       0.389 |   0.315 |   0.425 |    0.019 |    0.024 |
| C. Hybrid: isolation_forest     |          0.36  |          0.487 |       0.316 |       0.419 |   0.34  |   0.441 |    0.021 |    0.026 |

## ML on rule-passing rows only, native tier

| model               |   residual_rows |   residual_fraud |   tp |   fp |   fn |    tn |   precision |   recall |    f1 |   fpr |   fnr |   accuracy |   roc_auc |   pr_auc |
|:--------------------|----------------:|-----------------:|-----:|-----:|-----:|------:|------------:|---------:|------:|------:|------:|-----------:|----------:|---------:|
| logistic_regression |           39891 |             1709 |  975 |  885 |  734 | 37297 |       0.524 |    0.571 | 0.546 | 0.023 | 0.429 |      0.959 |     0.916 |    0.608 |
| random_forest       |           39891 |             1709 | 1282 |  881 |  427 | 37301 |       0.593 |    0.75  | 0.662 | 0.023 | 0.25  |      0.967 |     0.963 |    0.764 |
| isolation_forest    |           39891 |             1709 |  566 |  701 | 1143 | 37481 |       0.447 |    0.331 | 0.38  | 0.018 | 0.669 |      0.954 |     0.847 |    0.393 |

## Per-scenario recall, native tier

| scenario                       |   ('recall', 'hybrid_random_forest') |   ('recall', 'ml_random_forest') |   ('recall', 'rules_only') |   ('attack_recall', 'hybrid_random_forest') |   ('attack_recall', 'ml_random_forest') |   ('attack_recall', 'rules_only') |
|:-------------------------------|-------------------------------------:|---------------------------------:|---------------------------:|--------------------------------------------:|----------------------------------------:|----------------------------------:|
| combined                       |                                 0.79 |                             0.77 |                       0.1  |                                        0.95 |                                    0.95 |                              0.1  |
| cumulative_offline_spend       |                                 0.69 |                             0.69 |                       0.02 |                                        0.96 |                                    0.94 |                              0.06 |
| device_change                  |                                 0.68 |                             0.7  |                       0.01 |                                        0.7  |                                    0.72 |                              0.02 |
| double_spend                   |                                 1    |                             0.96 |                       1    |                                        1    |                                    0.96 |                              1    |
| large_amount                   |                                 0.9  |                             0.92 |                       0    |                                        0.9  |                                    0.92 |                              0    |
| long_offline_suspicious        |                                 0.73 |                             0.75 |                       0.01 |                                        0.91 |                                    0.94 |                              0.02 |
| new_beneficiary_unusual_amount |                                 0.98 |                             0.98 |                       0.06 |                                        1    |                                    1    |                              0.05 |
| replay_duplicate               |                                 0.92 |                             0.84 |                       0.92 |                                        0.92 |                                    0.84 |                              0.92 |
| rollback                       |                                 0.39 |                             0.39 |                       0.05 |                                        0.5  |                                    0.48 |                              0.06 |
| velocity_burst                 |                                 0.82 |                             0.83 |                       0.01 |                                        0.91 |                                    0.91 |                              0.02 |

## Unseen-scenario recall (hybrid, RF), native tier

| scenario                       |   seen |   unseen |   rules |
|:-------------------------------|-------:|---------:|--------:|
| combined                       |   0.79 |     0.71 |    0.1  |
| cumulative_offline_spend       |   0.69 |     0.24 |    0.02 |
| device_change                  |   0.68 |     0.61 |    0.01 |
| double_spend                   |   1    |     1    |    1    |
| large_amount                   |   0.9  |     0.62 |    0    |
| long_offline_suspicious        |   0.73 |     0.63 |    0.01 |
| new_beneficiary_unusual_amount |   0.98 |     0.91 |    0.06 |
| replay_duplicate               |   0.92 |     0.92 |    0.92 |
| rollback                       |   0.39 |     0.39 |    0.05 |
| velocity_burst                 |   0.82 |     0.13 |    0.01 |
