# Customer Data Masking — User Guide

This tool replaces customer codes and names with anonymous tokens (`CUST_0001`, `NAME_0001` etc.) before sending a file externally, and restores the originals when the file comes back.

---

## Files You Need

| File | Purpose |
|---|---|
| `mask_columns.py` | The script — copy this to the new machine |
| `mapping.xlsx` | Auto-created on first run — **keep this private, never share it** |

---

## One-Time Setup (do this once per machine)

Open Terminal and run these commands one by one:

```
cd Desktop/HEDIS
python3 -m venv venv
source venv/bin/activate
pip install pandas openpyxl
```

You should see `(venv)` at the start of your terminal prompt after the second command.

---

## Every Time You Use It

Open Terminal and activate the virtual environment first:

```
cd Desktop/HEDIS
source venv/bin/activate
```

Then run the steps below.

---

## STEP 1 — Before sending to the external company

```
python mask_columns.py mask --input your_file.xlsx --output masked.xlsx --mapping mapping.xlsx
```

Replace `your_file.xlsx` with your actual filename.

**What happens:**
- `mapping.xlsx` is created automatically on first run with all your customers mapped
- If `mapping.xlsx` already exists, it is updated — existing customers keep their tokens, new ones are appended
- `masked.xlsx` is the file to send to the external company

**Example output — first time (300 customers):**
```
300 new customer(s) added to mapping.
Mapping saved: mapping.xlsx  (300 total customers)
Masked file saved: masked.xlsx  (1500 rows)
```

**Example output — next time (same file + 20 new customers):**
```
Existing mapping loaded: mapping.xlsx  (300 customers already mapped)
20 new customer(s) added to mapping.
Mapping saved: mapping.xlsx  (320 total customers)
Masked file saved: masked.xlsx  (1600 rows)
```

There is no limit — if you add 1000 new customers it simply grows to 1300. One mapping file, always.

---

## STEP 2 — After receiving the forecast back

```
python mask_columns.py restore --input forecast_returned.xlsx --output restored.xlsx --mapping mapping.xlsx
```

Replace `forecast_returned.xlsx` with whatever filename the company sent back.

**What happens:**
- Real customer codes and names are restored
- Any forecast columns the company added pass through unchanged
- `restored.xlsx` is your final file

---

## What the External Company Sees

Their file will look like this — real customer data is hidden:

| Region | CustomerCode | CustomerName | Period | ... |
|---|---|---|---|---|
| USA & Canada | CUST_0001 | NAME_0001 | 01.2021 | ... |
| USA & Canada | CUST_0002 | NAME_0002 | 01.2021 | ... |

Your private `mapping.xlsx` holds the key:

| Original_Code | Original_Name | Masked_Code | Masked_Name |
|---|---|---|---|
| 0000149639 | DANTRADE B.V. | CUST_0001 | NAME_0001 |
| 0001200030 | Brust Beverage Company Limited | CUST_0002 | NAME_0002 |
| ... | ... | ... | ... |

---

## If Customer Columns Are in a Different Position

By default the script looks for customer code in column 2 and name in column 3.
If your file has them elsewhere, use the column header name — this works regardless of position:

```
python mask_columns.py mask --input your_file.xlsx --output masked.xlsx --mapping mapping.xlsx --code-col CustomerCode --name-col CustomerName
```

Or use the column number if you know it:

```
python mask_columns.py mask --input your_file.xlsx --output masked.xlsx --mapping mapping.xlsx --code-col 5 --name-col 6
```

This works for both `mask` and `restore`.

---

## Quick Reference

| Task | Command |
|---|---|
| Mask before sending | `python mask_columns.py mask --input YOUR_FILE.xlsx --output masked.xlsx --mapping mapping.xlsx` |
| Restore after receiving | `python mask_columns.py restore --input RETURNED_FILE.xlsx --output restored.xlsx --mapping mapping.xlsx` |

---

## Important Reminders

- Never send `mapping.xlsx` to the external company — it contains all real customer data.
- Without `mapping.xlsx` you cannot restore a returned file. Keep it safe.
- The same `mapping.xlsx` works for every file — any format (`.xlsx`, `.xls`, `.csv`), any column order.
- You do not need to create `mapping.xlsx` manually — it is always auto-created or updated.
