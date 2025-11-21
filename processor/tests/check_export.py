import json, math, sys
from pathlib import Path

def close(a, b, rt=1e-6, at=1e-6):
    try:
        return math.isclose(a, b, rel_tol=rt, abs_tol=at)
    except Exception:
        return False

def check_file(path):
    p = Path(path)
    if not p.exists():
        print(f"File not found: {p}")
        return
    bad = 0
    with p.open(encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            try:
                o = json.loads(line)
            except Exception as e:
                bad += 1
                print(f"{i}: JSON decode error: {e}")
                continue

            def err(msg):
                nonlocal bad
                bad += 1
                print(f"{i}: {msg}")

            # FVG
            if o.get("fvg_detected"):
                top, bot, gap = o.get("fvg_top"), o.get("fvg_bottom"), o.get("fvg_gap_size")
                if top is None or bot is None or gap is None:
                    err("FVG missing top/bottom/gap")
                else:
                    if not (top > bot):
                        err(f"FVG ordering top<=bot ({top},{bot})")
                    if not close(top - bot, gap):
                        err(f"FVG gap mismatch top-bot={top-bot} gap={gap}")

            # OB
            if o.get("ob_detected"):
                ot, obm = o.get("ob_top"), o.get("ob_bottom")
                if ot is None or obm is None:
                    err("OB missing top/bottom")
                elif not (ot > obm):
                    err(f"OB ordering top<=bottom ({ot},{obm})")

            # Structure
            if o.get("choch_detected") and (o.get("choch_type") in (None, "none")):
                err("choch_type missing")
            if o.get("bos_detected") and (o.get("bos_type") in (None, "none")):
                err("bos_type missing")

            # Stop placement fields present
            for fld in ("fvg_top", "fvg_bottom", "fvg_type", "nearest_ob_top", "nearest_ob_bottom", "last_swing_high", "last_swing_low"):
                if fld not in o:
                    err(f"stop_placement missing {fld}")

            # Target placement fields present
            for fld in ("recent_swing_high", "recent_swing_low"):
                if fld not in o:
                    err(f"target_placement missing {fld}")

            # Volume consistency
            vol = o.get("volume"); bv = o.get("buy_volume"); sv = o.get("sell_volume"); delta = o.get("delta")
            if None not in (vol, bv, sv) and not close(bv + sv, vol):
                err(f"buy+sell != volume ({bv+sv} vs {vol})")
            if None not in (bv, sv, delta) and not close(bv - sv, delta):
                err(f"delta != buy-sell ({delta} vs {bv-sv})")

            # Non-negative metrics
            for fld in ("atr_14","adx_14"):
                if o.get(fld) is not None and o[fld] < 0:
                    err(f"{fld} negative ({o[fld]})")

            # HTF/Liquidity presence
            for fld in ("htf_high","htf_low","htf_close","htf_ema_20","htf_ema_50","htf_is_swing_high","htf_is_swing_low",
                        "nearest_liquidity_high","nearest_liquidity_low","liquidity_high_type","liquidity_low_type"):
                if fld not in o:
                    err(f"missing {fld}")

            # Structure context presence
            for fld in ("choch_detected","bos_detected","choch_bars_ago","bos_bars_ago","current_trend","last_structure_break"):
                if fld not in o:
                    err(f"structure_context missing {fld}")

            # Volume divergence presence
            for fld in ("is_swing_high","is_swing_low","cumulative_delta"):
                if fld not in o:
                    err(f"volume_divergence missing {fld}")

    print(f"Done. Bad count: {bad}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python check_export.py <path_to_jsonl>")
        return
    check_file(sys.argv[1])

if __name__ == "__main__":
    main()
