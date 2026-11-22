# Agentic BI with SQLite

A hands-on business intelligence tutorial that traces a change in net revenue from the regional total to the city and operational measures behind it. The notebook uses a deterministic workflow and a synthetic sales warehouse.

[![Tests](https://github.com/ShirMamia/agentic-bi/actions/workflows/tests.yml/badge.svg)](https://github.com/ShirMamia/agentic-bi/actions/workflows/tests.yml)

## Explore the notebook

Open [`agentic_bi.ipynb`](agentic_bi.ipynb) in Jupyter or VS Code and run the cells from top to bottom from the repository folder. The demo uses the Python standard library, runs offline, and needs no API keys. All transactions and contextual reports are fictional.

1. **Warehouse only.** Compare two months in SQLite, then inspect orders, cancellations, payment failures, and delivery time in the city with the largest decline.
2. **Relevant context.** Add a fictional delivery report and see when the rules accept it as supporting context.
3. **Noisy context.** Mix in sources with a different city, month, or topic and compare the resulting evidence.
4. **Counterfactual.** Change June revenue and see the previous decline and its operational hypothesis disappear.

## Read the evidence

- Net revenue is gross revenue minus discounts and refunds.
- Cancellation and payment failure rates use checkout attempts as the denominator. Delivery time is weighted by reported orders.
- Comparisons require observations for the same cities in both months. A missing period returns an insufficient-data result.
- The external reports are fixtures. Matching location, period, and observed delivery pressure makes a report relevant for investigation. A causal conclusion would require further evidence.

The reusable investigation is in [`agentic_bi.py`](agentic_bi.py). [`sample_warehouse.py`](sample_warehouse.py) builds the example in an in-memory SQLite database. After seeding, the notebook switches the connection to read-only for its analyses.

## Run the tests

```sh
python -m unittest discover -v
```
