#!/usr/bin/env python3
"""Check CHoCH naming convention in data"""
import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from processor.modules.fix14_mgann_swing import Fix14MgannSwing

export_dir = Path(r"C:\Users\Administrator\Documents\NinjaTrader 8\smc_exports_enhanced")
test_file = list(export_dir.glob("*M1_20250904.jsonl"))[0]

mgann = Fix14MgannSwing()

print("Checking CHoCH naming convention...\n")

choch_events = []

with open(test_file, 'r') as f:
    for line in f:
        bar = json.loads(line.strip())
        
        # Flatten
        bar_obj = bar.get('bar', {})
        vol_stats = bar_obj.get('volume_stats', {})
        if vol_stats:
            bar['delta'] = vol_stats.get('delta_close', 0)
            bar['volume'] = vol_stats.get('total_volume', 0)
        bar['ext_choch_up'] = bar_obj.get('ext_choch_up', False)
        bar['ext_choch_down'] = bar_obj.get('ext_choch_down', False)
        bar['ext_dir'] = bar_obj.get('ext_dir', 0)
        
        bar = mgann.process_bar(bar)
        
        if bar.get('ext_choch_up') or bar.get('ext_choch_down'):
            choch_events.append({
                'bar': bar.get('bar_index'),
                'choch_up': bar.get('ext_choch_up'),
                'choch_down': bar.get('ext_choch_down'),
                'ext_dir': bar.get('ext_dir'),
                'price': bar.get('close'),
            })

print(f"Found {len(choch_events)} CHoCH events:\n")

for i, event in enumerate(choch_events[:5]):
    print(f"{i+1}. Bar {event['bar']}:")
    if event['choch_up']:
        print(f"   CHoCH UP fired")
    if event['choch_down']:
        print(f"   CHoCH DOWN fired")
    print(f"   ext_dir at this bar: {event['ext_dir']}")
    print(f"   → Interpretation: CHoCH marks change TO direction = {event['ext_dir']}")
    print()

print("=" * 70)
print("CONCLUSION:")
print("If ext_dir matches CHoCH direction, then:")
print("  CHoCH UP = breaks UP → new UPTREND → LONG setups")
print("  CHoCH DOWN = breaks DOWN → new DOWNTREND → SHORT setups")
