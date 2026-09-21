#!/usr/bin/env python3
"""
Mask or restore customer columns in Excel/CSV files using a mapping table.

Usage:
    # Mask before sending (generates mapping file + masked output)
    python mask_columns.py mask --input customers.xlsx --output masked.xlsx --mapping mapping.xlsx

    # Restore after receiving back with forecasts
    python mask_columns.py restore --input forecast_returned.xlsx --output restored.xlsx --mapping mapping.xlsx
"""

import argparse
import sys
from pathlib import Path

import pandas as pd


def detect_delimiter(filepath: str) -> str:
    ext = Path(filepath).suffix.lower()
    if ext == ".csv":
        return ","
    return "\t"


def read_file(filepath: str) -> pd.DataFrame:
    ext = Path(filepath).suffix.lower()
    if ext in (".xlsx", ".xls"):
        return pd.read_excel(filepath, dtype=str).fillna("")
    else:
        delim = detect_delimiter(filepath)
        return pd.read_csv(filepath, sep=delim, dtype=str, keep_default_na=False)


def write_file(df: pd.DataFrame, filepath: str):
    ext = Path(filepath).suffix.lower()
    if ext in (".xlsx", ".xls"):
        df.to_excel(filepath, index=False)
    else:
        delim = detect_delimiter(filepath)
        df.to_csv(filepath, sep=delim, index=False)


def resolve_column(col_arg: str, df: pd.DataFrame) -> str:
    """Accept either a column header name or a 1-based column number."""
    if col_arg.isdigit():
        idx = int(col_arg) - 1
        if idx < 0 or idx >= len(df.columns):
            print(f"ERROR: Column {col_arg} is out of range (file has {len(df.columns)} columns).", file=sys.stderr)
            sys.exit(1)
        return df.columns[idx]
    else:
        if col_arg not in df.columns:
            print(f"ERROR: Column '{col_arg}' not found. Available columns: {list(df.columns)}", file=sys.stderr)
            sys.exit(1)
        return col_arg


def load_existing_mapping(mapping_path: str) -> pd.DataFrame:
    ext = Path(mapping_path).suffix.lower()
    if ext in (".xlsx", ".xls"):
        return pd.read_excel(mapping_path, dtype=str).fillna("")
    else:
        return pd.read_csv(mapping_path, dtype=str).fillna("")


def mask_file(args):
    df = read_file(args.input)

    code_col = resolve_column(args.code_col, df)
    name_col = resolve_column(args.name_col, df)

    # Load existing mapping if it exists, otherwise start fresh
    mapping_path = args.mapping
    if Path(mapping_path).exists():
        mapping = load_existing_mapping(mapping_path)
        next_id = len(mapping) + 1
        print(f"Existing mapping loaded: {mapping_path}  ({len(mapping)} customers already mapped)")
    else:
        mapping = pd.DataFrame(columns=["Original_Code", "Original_Name", "Masked_Code", "Masked_Name"])
        next_id = 1

    # Find customers in this file not yet in the mapping
    unique_customers = df[[code_col, name_col]].drop_duplicates()
    unique_customers.columns = ["Original_Code", "Original_Name"]
    already_mapped = set(mapping["Original_Code"].tolist())
    new_customers = unique_customers[~unique_customers["Original_Code"].isin(already_mapped)].reset_index(drop=True)

    if len(new_customers) > 0:
        new_customers["Masked_Code"] = [f"CUST_{str(next_id + i).zfill(4)}" for i in range(len(new_customers))]
        new_customers["Masked_Name"] = [f"NAME_{str(next_id + i).zfill(4)}" for i in range(len(new_customers))]
        mapping = pd.concat([mapping, new_customers], ignore_index=True)
        print(f"{len(new_customers)} new customer(s) added to mapping.")
    else:
        print("No new customers — all already in mapping.")

    # Save mapping table
    ext = Path(mapping_path).suffix.lower()
    if ext in (".xlsx", ".xls"):
        mapping.to_excel(mapping_path, index=False)
    else:
        mapping.to_csv(mapping_path, index=False)
    print(f"Mapping saved: {mapping_path}  ({len(mapping)} total customers)")

    # Apply masking to the data
    code_map = dict(zip(mapping["Original_Code"], mapping["Masked_Code"]))
    name_map = dict(zip(mapping["Original_Name"], mapping["Masked_Name"]))

    masked_df = df.copy()
    masked_df[code_col] = masked_df[code_col].map(code_map).fillna(masked_df[code_col])
    masked_df[name_col] = masked_df[name_col].map(name_map).fillna(masked_df[name_col])

    if Path(args.input).resolve() == Path(args.output).resolve():
        print("ERROR: input and output cannot be the same file.", file=sys.stderr)
        sys.exit(1)

    write_file(masked_df, args.output)
    print(f"Masked file saved: {args.output}  ({len(masked_df)} rows)")
    print(f"\nSend '{args.output}' to the external company.")
    print(f"Keep '{mapping_path}' private — you need it to restore the returned file.")


def restore_file(args):
    mapping_path = args.mapping
    ext = Path(mapping_path).suffix.lower()
    if not Path(mapping_path).exists():
        print(f"ERROR: Mapping file '{mapping_path}' not found.", file=sys.stderr)
        sys.exit(1)

    if ext in (".xlsx", ".xls"):
        mapping = pd.read_excel(mapping_path, dtype=str).fillna("")
    else:
        mapping = pd.read_csv(mapping_path, dtype=str).fillna("")

    # Reverse maps: masked -> original
    code_map = dict(zip(mapping["Masked_Code"], mapping["Original_Code"]))
    name_map = dict(zip(mapping["Masked_Name"], mapping["Original_Name"]))

    df = read_file(args.input)

    code_col = resolve_column(args.code_col, df)
    name_col = resolve_column(args.name_col, df)

    # Check that the column looks masked
    sample_val = df[code_col].iloc[0] if len(df) > 0 else ""
    if not str(sample_val).startswith("CUST_"):
        print(f"WARNING: Column {args.code_col} does not look masked (first value: '{sample_val}'). Proceeding anyway.", file=sys.stderr)

    restored_df = df.copy()
    restored_df[code_col] = restored_df[code_col].map(code_map).fillna(restored_df[code_col])
    restored_df[name_col] = restored_df[name_col].map(name_map).fillna(restored_df[name_col])

    if Path(args.input).resolve() == Path(args.output).resolve():
        print("ERROR: input and output cannot be the same file.", file=sys.stderr)
        sys.exit(1)

    write_file(restored_df, args.output)
    print(f"Restored file saved: {args.output}  ({len(restored_df)} rows)")


def main():
    parser = argparse.ArgumentParser(
        description="Mask/restore customer columns in Excel or CSV files using a mapping table."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--input", required=True, help="Input file (.xlsx or .csv/.tsv)")
    shared.add_argument("--output", required=True, help="Output file (.xlsx or .csv/.tsv)")
    shared.add_argument("--mapping", default="mapping.xlsx", help="Mapping file path (default: mapping.xlsx)")
    shared.add_argument("--code-col", default="2", help="Column for customer code: header name (e.g. 'CustomerCode') or 1-based number (default: 2)")
    shared.add_argument("--name-col", default="3", help="Column for customer name: header name (e.g. 'CustomerName') or 1-based number (default: 3)")

    subparsers.add_parser("mask", parents=[shared], help="Mask columns before sending")
    subparsers.add_parser("restore", parents=[shared], help="Restore columns after receiving back")

    args = parser.parse_args()

    if args.command == "mask":
        mask_file(args)
    else:
        restore_file(args)


if __name__ == "__main__":
    main()
