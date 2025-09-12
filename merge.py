from bson import decode_all
import csv

sx_fold = 'sx_fold.csv'
bids = 'bids.csv'
bids_with_fold = 'bids_with_fold.csv'

def read_bson():
    with open('../../02_Data/tripitaka-aux/sx_fold.bson', 'rb') as f:
        data = f.read()
        documents = decode_all(data)
    
    if documents:
        # Collect all unique keys from all documents
        all_keys = set()
        for doc in documents:
            all_keys.update(doc.keys())
        all_keys = sorted(all_keys)  # Optional: sort keys for consistent column order

        with open('sx_fold.csv', 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=all_keys)
            writer.writeheader()
            writer.writerows(documents)

def merge_fold_id_from_db_to_extracted_csv():
    bid_to_fold = {}
    with open(sx_fold, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            bid = row.get('bid')
            fold_id = row.get('fold_id')
            if bid and fold_id:
                bid_to_fold[bid] = fold_id

    with open(bids, newline='', encoding='utf-8') as f_in, open(bids_with_fold, 'w', newline='', encoding='utf-8') as f_out:
        reader = csv.DictReader(f_in)
        fieldnames = reader.fieldnames + ['fold_id']
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        for row in reader:
            bid = row.get('bid')
            row['fold_id'] = bid_to_fold.get(bid, '')
            writer.writerow(row)

if __name__ == "__main__":
    merge_fold_id_from_db_to_extracted_csv()