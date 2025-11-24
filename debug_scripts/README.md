# Debug Scripts

This folder contains debug and test scripts used during development.

## Active Scripts (Keep)

### Testing & Verification
- `test_module14_real_data.py` - Main test script for Module 14 with real data
- `test_module15_m5.py` - Test script for Module 15 M5 context
- `verify_m5_export.py` - Verify M5 fields in JSONL export

### Visualization
- `vis.py` - Main simplified visualizer (internal swings + wave strength)
- `vis_leg_index.py` - Leg index visualization with zigzag
- `visualizer_mgann_plotly.py` - Original full visualizer

## Archived Debug Scripts (Moved to debug_scripts/)

These were used during development but are no longer needed:

- `debug_leg_index.py` - Debug leg index field
- `debug_m5_events.py` - Debug M5 event timing
- `debug_module15_swing.py` - Debug Module 15 swing detection
- `debug_waves.py` - Debug wave calculations
- `check_module14_fields.py` - Early field verification
- `verify_m5_logic.py` - M5 logic verification
- `verify_new_fields.py` - Verify Module 14 new fields
- `test_wave_strength.py` - Wave strength testing
- `test_colors.py` - Colorscale testing
- `test_wave_colors.py` - Wave color verification

## Obsolete Files

### Module 15 (Not Needed - Using C# Export Instead)
- `processor/modules/fix15_m5_context.py` - DELETE (M5 from C# indicator)
- `test_module15_m5.py` - KEEP for reference but not used

## Cleanup Done

- ✅ Moved debug scripts to `debug_scripts/` folder
- ✅ Kept essential test/visualization scripts in root
- ⏳ TODO: Delete `processor/modules/fix15_m5_context.py` (Phase 3.5 abandoned)
