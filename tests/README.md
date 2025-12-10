# NLP Bot Accuracy Evaluation

This folder contains the testing infrastructure for evaluating the accuracy of our AI-powered NLP function (`matcher.py`) that extracts IFC element GUIDs from natural language text.

## Files

### 📊 `nlp_accuracy_evaluation.ipynb`

Interactive Jupyter notebook that runs the complete evaluation pipeline:

- Loads test cases from `test_data.json`
- Runs NLP matcher on each test case
- Compares results against expected GUIDs
- Calculates accuracy metrics (Exact Match, Precision, Recall, F1 Score)
- Generates visualizations and exports results

### 📝 `test_data.json`

Human-annotated test cases in JSON format. Each test case contains:

```json
{
  "test_id": 1,
  "input_text": "Update all doors to inspected",
  "expected_guids": ["guid1", "guid2", ...],
  "description": "Brief description of test case"
}
```

## How to Use

### 1. Prepare Test Data

Edit `test_data.json` and add your human-annotated test cases:

- `input_text`: Natural language message the bot receives
- `expected_guids`: List of correct IFC GlobalIds that should be returned
- `description`: Optional description for documentation

### 2. Run Evaluation

Open `nlp_accuracy_evaluation.ipynb` in Jupyter and run all cells:

```bash
jupyter notebook nlp_accuracy_evaluation.ipynb
```

Or use VS Code's Jupyter extension to run the notebook interactively.

### 3. Review Results

The notebook will display:

- **Summary Metrics**: Overall exact match rate, precision, recall, F1 score
- **Per-Test Breakdown**: Detailed results for each test case
- **Visualizations**: Charts showing accuracy distribution and metrics
- **Threshold Analysis**: Percentage of tests achieving different accuracy levels (50%, 60%, 70%, etc.)

### 4. Export Results

Results are automatically exported to:

- `nlp_evaluation_results.csv`: Detailed per-test-case results
- `nlp_evaluation_summary.txt`: Summary statistics

## Metrics Explained

### Exact Match Rate

Percentage of test cases where the NLP bot returned **exactly** the expected set of GUIDs (no more, no less).

### Precision

Of all GUIDs returned by the NLP bot, what percentage were correct?

```
Precision = True Positives / (True Positives + False Positives)
```

### Recall

Of all expected GUIDs, what percentage did the NLP bot find?

```
Recall = True Positives / (True Positives + False Negatives)
```

### F1 Score

Harmonic mean of Precision and Recall (balanced measure):

```
F1 = 2 × (Precision × Recall) / (Precision + Recall)
```

## Example Output

```
============================================================
OVERALL ACCURACY SUMMARY
============================================================
Metric                 Percentage    Raw Score
Exact Match Rate       66.67%        2/3
Average Precision      83.33%        0.8333
Average Recall         75.00%        0.7500
Average F1 Score       78.57%        0.7857
============================================================
```

## Updating Test Cases

To add new test cases, append to `test_data.json`:

```json
{
  "test_id": 4,
  "input_text": "Mark all MEP systems as installed",
  "expected_guids": ["guid_mep_1", "guid_mep_2"],
  "description": "MEP-specific test with status change"
}
```

## Troubleshooting

### Import Error for NLP Module

Make sure the notebook can find the `NLP/matcher.py` module. The notebook adds the parent directory to the Python path automatically.

### Matcher Function Name

If your matcher function has a different name, update the import in the second cell:

```python
from NLP.matcher import your_function_name  # Change this
```

### Adjusting Function Call

Update the function call in the third cell to match your matcher's signature:

```python
returned_guids = your_function_name(input_text, additional_params)
```

## Future Enhancements

- [ ] Add category-based analysis (doors vs windows vs structural elements)
- [ ] Include execution time metrics
- [ ] Add confusion matrix visualization
- [ ] Support for multi-label classification metrics
- [ ] Automated test case generation from actual Telegram logs
