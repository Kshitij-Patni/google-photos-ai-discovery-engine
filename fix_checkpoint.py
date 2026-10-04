import json

checkpoint_path = "data/enriched/corpus_classified_checkpoint.json"
with open(checkpoint_path, "r") as f:
    records = json.load(f)

valid_records = []
for r in records:
    arch = r.get("archetype_classification", {})
    if arch.get("reasoning") != "Failed to classify or insufficient context.":
        valid_records.append(r)

with open(checkpoint_path, "w") as f:
    json.dump(valid_records, f, indent=2)

print(f"Original records: {len(records)}")
print(f"Valid records kept: {len(valid_records)}")
print(f"Removed for retry: {len(records) - len(valid_records)}")
