# CV project entry for Financial Services Data Analytics

**FDIC Financial Data Pipeline & Bank-Failure Early Warning** | Python, SQL, Polars, pandas, PySpark, scikit-learn

- Built and audited a financial-data pipeline covering **1.68 million quarterly reports and 87 source fields**, with resumable acquisition, typed Parquet storage and accounting/missing-data reconciliation.
- Benchmarked pandas and Polars transformations and reconciled results with local PySpark; measured approximately **3.8x smaller Parquet storage** on a matched data projection.
- Evaluated risk models using time-ordered development folds and a frozen holdout, with precision-recall, event recall, lead time and analyst-review workload scenarios; documented when simpler baselines generalized better.

Add the actual GitHub URL after creating the repository. Use two bullets if space is limited. Only claim skills and code you can explain independently in an interview.

## Interview framing

Start with the business question: which banks should an analyst review, with what workload? Then explain the quality issue you investigated, how the train/test boundary was protected, and what the held-out comparison contradicted. Do not describe 87 fields as 87 final features, 87% event recall as precision, scenario losses as real savings, or this academic project as EY experience.
