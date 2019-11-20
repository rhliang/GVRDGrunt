#! /usr/bin/env python

import argparse
import json


def main():
    parser = argparse.ArgumentParser("Convert a table's scan output to something suitable for batch writing.")
    parser.add_argument("scan_json", help="Output of a DynamoDB scan.")
    parser.add_argument("table_name", help="The name of the table to write to")
    parser.add_argument("batch_write_prefix", help="prefix for JSON files suitable for batch-write-item.")
    args = parser.parse_args()

    with open(args.scan_json, "r") as f:
        scan_dict = json.load(f)

    all_items = scan_dict["Items"]
    # Break this into chunks of 25.

    idx = 1
    while (idx - 1) * 25 < len(all_items):
        start = (idx - 1) * 25
        end = min(len(all_items), idx * 25)
        curr_items = all_items[start:end]

        batch_write_dict = {}
        batch_write_dict[args.table_name] = [{"PutRequest": {"Item": x}} for x in curr_items]

        with open(f"{args.batch_write_prefix}_{idx}.json", "w") as f:
            json.dump(batch_write_dict, f, indent=4)

        idx += 1


if __name__ == "__main__":
    main()
