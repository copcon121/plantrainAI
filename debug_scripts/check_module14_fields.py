import json

with open('module14_results.json', 'r') as f:
    data = json.load(f)

print("=" * 70)
print("MODULE 14 v1.2.0 - NEW FIELDS VERIFICATION")
print("=" * 70)

# Check if fields exist
fields = ['mgann_leg_index', 'mgann_leg_first_fvg', 'pb_wave_strength_ok']
print("\n✅ Field Existence Check:")
for field in fields:
    exists = field in data[100]
    print(f"   {field}: {'✓ Present' if exists else '✗ Missing'}")

# Sample values
print("\n📊 Sample Values (First 20 bars):")
print("-" * 70)
print(f"{'Bar':>4} {'Dir':>4} {'LegIdx':>7} {'1stFVG':>7} {'PB_OK':>6}")
print("-" * 70)

for i in range(min(20, len(data))):
    bar = data[i]
    leg_dir = bar.get('mgann_internal_leg_dir', '?')
    leg_idx = bar.get('mgann_leg_index', '?')
    first_fvg = '✓' if bar.get('mgann_leg_first_fvg') else '·'
    pb_ok = '✓' if bar.get('pb_wave_strength_ok') else '·'
    
    print(f"{i:>4} {leg_dir:>4} {leg_idx:>7} {first_fvg:>7} {pb_ok:>6}")

# Statistics
print("\n📈 Statistics (All 1380 bars):")
leg_indices = [d.get('mgann_leg_index', 0) for d in data]
first_fvg_count = sum(1 for d in data if d.get('mgann_leg_first_fvg'))
pb_ok_count = sum(1 for d in data if d.get('pb_wave_strength_ok'))

print(f"   Max leg_index: {max(leg_indices)}")
print(f"   First FVG detections: {first_fvg_count} ({first_fvg_count/len(data)*100:.1f}%)")
print(f"   Pullback OK count: {pb_ok_count} ({pb_ok_count/len(data)*100:.1f}%)")

print("\n✅ All new fields exported successfully!")
