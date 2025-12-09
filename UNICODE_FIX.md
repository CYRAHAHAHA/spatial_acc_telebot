# Unicode Encoding Error Fix - Windows Console Issue

## Error Analysis: December 5, 2025

### Error Message:

```
ERROR reading assets_total.csv: 'charmap' codec can't encode character '\u2713' in position 0: character maps to <undefined>
```

---

## Root Cause

**Character:** `✓` (Unicode U+2713 - CHECK MARK)  
**Issue:** Windows console uses CP1252 encoding which cannot display Unicode checkmark characters  
**Impact:** Python's `print()` function crashes when trying to output this character on Windows

---

## Where the Error Occurred

### File: `root/app/functions/update_status.py`

**Three problematic lines:**

1. **Line 41** - In `_lookup_status_id_by_label()`:

   ```python
   print(f"✓ Match found! status_id='{found_status_id}'")
   ```

2. **Line 75** - In `_resolve_asset_info_from_guid()`:

   ```python
   print(f"✓ Asset found! B3F_id='{asset_info['B3F_id']}', status_set_id='{asset_info['status_set_id']}'")
   ```

3. **Line 157** - In `update_assets()`:
   ```python
   print("✓ SUCCESS: Asset status updated")
   ```

---

## The Fix

### Changed From (❌):

```python
print(f"✓ Match found! status_id='{found_status_id}'")
print(f"✓ Asset found! B3F_id='{asset_info['B3F_id']}'...")
print("✓ SUCCESS: Asset status updated")
```

### Changed To (✅):

```python
print(f"[OK] Match found! status_id='{found_status_id}'")
print(f"[OK] Asset found! B3F_id='{asset_info['B3F_id']}'...")
print("[SUCCESS] Asset status updated")
```

---

## Why This Happened

### Context:

This is the same type of issue we fixed earlier in `telebot/bot_logger.py` with the robot emoji (`🤖`).

### Windows Console Limitations:

- **Default encoding:** CP1252 (Windows-1252)
- **Supports:** Basic ASCII + extended Latin characters
- **Cannot display:** Most Unicode symbols (emojis, special marks, etc.)

### Linux/Railway (Production):

- **Default encoding:** UTF-8
- **Supports:** Full Unicode character set
- **No issues** with these characters

**Result:** Code works on Railway but crashes on Windows during local development.

---

## Impact on Bot Workflow

### What Was Happening:

1. User sends Telegram message:

   ```
   [UPDATE]
   GUID: 2cXV28XOjE6f6irgi0COy$
   Status: Ordered
   ```

2. Bot calls Flask API → `update_status.py`

3. Function `_resolve_asset_info_from_guid()` searches CSV

4. **When asset is found**, tries to print:

   ```python
   print(f"✓ Asset found! B3F_id='...'")
   ```

5. **CRASH** - Windows console can't encode `✓` character

6. Exception thrown → CSV reading stops

7. Function returns `None` → "Asset not found" error

### Result:

Even though the asset **exists in the CSV**, the function fails before returning it.

---

## Verification

### Before Fix:

```log
Looking up asset with GUID: '2cXV28XOjE6f6irgi0COy$'
ERROR reading assets_total.csv: 'charmap' codec can't encode character '\u2713' in position 0: character maps to <undefined>
FAILED: Could not find asset with GUID: 2cXV28XOjE6f6irgi0COy$
```

### After Fix (Expected):

```log
Looking up asset with GUID: '2cXV28XOjE6f6irgi0COy$'
[OK] Asset found! B3F_id='6e5b8d6d-1dae-4407-8450-4159b56d53fd', status_set_id='22974b8d-dac6-41fe-b010-4aa2fb19b623'

Step 1 complete:
  asset_id (B3F_id): 6e5b8d6d-1dae-4407-8450-4159b56d53fd
  status_set_id: 22974b8d-dac6-41fe-b010-4aa2fb19b623
```

---

## Testing

### Test Asset from Your CSV:

**GUID:** `2cXV28XOjE6f6irgi0COy$`  
**Expected Match:**

```csv
6e5b8d6d-1dae-4407-8450-4159b56d53fd,,,IfcDoor::M_Door-Interior-Double-Full Glass-Wood:1500 x 2000mm:353875,4,22974b8d-dac6-41fe-b010-4aa2fb19b623,d5e30041-2da4-4407-a648-9ddc04b215fc,2cXV28XOjE6f6irgi0COy$
```

**Bot message to test:**

```
[UPDATE]
GUID: 2cXV28XOjE6f6irgi0COy$
Status: Ordered
```

---

## Best Practices to Avoid This

### 1. Use ASCII-Only Characters in Print Statements

```python
# ❌ BAD - Unicode symbols
print("✓ Success")
print("✗ Failed")
print("→ Processing")
print("🤖 Bot started")

# ✅ GOOD - ASCII text
print("[OK] Success")
print("[FAIL] Failed")
print("[PROCESS] Processing")
print("[BOT] Bot started")
```

### 2. Alternative: Handle Encoding Explicitly

```python
import sys

# Set stdout encoding to UTF-8 (if supported)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
```

### 3. For Files: Always Use UTF-8

```python
# ✅ Already doing this correctly
with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
```

---

## Files Fixed

### ✅ `root/app/functions/update_status.py`

- Line 41: `✓` → `[OK]`
- Line 75: `✓` → `[OK]`
- Line 157: `✓` → `[SUCCESS]`

### ✅ `telebot/bot_logger.py` (Fixed Previously)

- Line 1189: `🤖` → `[BOT]`

---

## Summary

**Problem:** Unicode checkmark character (`✓`) crashes on Windows console  
**Solution:** Replace with ASCII text (`[OK]`, `[SUCCESS]`)  
**Result:** Bot can now successfully look up assets and update statuses locally

**Status:** ✅ FIXED - Ready to test!

---

## Next Steps

1. **Restart Flask server:**

   ```bash
   bash stop_all.sh
   bash start_all.sh
   ```

2. **Test with Telegram:**

   ```
   [UPDATE]
   GUID: 2cXV28XOjE6f6irgi0COy$
   Status: Ordered
   ```

3. **Check logs:**

   ```bash
   cat logs/flask_webapp.log
   ```

   Should see:

   ```
   Looking up asset with GUID: '2cXV28XOjE6f6irgi0COy$'
   [OK] Asset found! B3F_id='6e5b8d6d-1dae-4407-8450-4159b56d53fd'
   ```

4. **Verify ACC update** - Check if status actually changed in Autodesk Construction Cloud

---

**Key Takeaway:** Avoid Unicode symbols in print statements when developing on Windows. Use ASCII-safe alternatives like `[OK]`, `[FAIL]`, `[SUCCESS]`.
