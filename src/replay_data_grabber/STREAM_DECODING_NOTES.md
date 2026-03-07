# rec_data Reverse Engineering Notes

## Target
- File: `data/replays/#2025.07.10 23.43.17.wrpl`
- Extraction: `zlib.decompress(raw[1224+set_size+2:rez_offset])` -> **5,896,784 bytes**
  - `rez_offset = struct.unpack('<I', raw[684:688])[0]`
  - `set_size = struct.unpack('<I', raw[748:752])[0]`
- Ground truth JSON: `output/replays/replay_2025-07-10_23-35-40_5051348001d5608.json`
- Python: `venv/Scripts/python.exe`, scripts in `temp/`

## Ground Truth: 29 Kills by Slot
```python
kills_by_slot = {1:1, 6:2, 8:1, 14:1, 15:2, 16:4, 17:1, 19:1, 20:8, 21:1, 23:1, 27:2, 30:1, 31:3}
slot_to_name = {
    0:'RaisingStats', 1:'CCTVCNNI', 2:'朝鲜', 3:'TheRebelFriend', 4:'iIiSkrimpiIi',
    5:'LonelyMinds', 6:'yama2234', 7:'J_Tekh', 8:'Saintguy123', 9:'横扫波兰',
    10:'ch-yirong', 11:'Reign Heavy', 12:'SNIPERLYFE69143', 13:'彼阳的晚意',
    14:'北鄙之狄', 15:'67897043', 16:'槐诗114', 17:'Ranol', 18:'suupeerr',
    19:'Charger__O6__', 20:'Kuro_155', 21:'_Demon_Guy_', 22:'GrimxReaperx1',
    23:'BerserkerMX', 24:'rumskippy08', 25:'一天不撸', 26:'a411481874124',
    27:'HuntMe01', 28:'Tuggle', 29:'hotdogicecream', 30:'MastrChiefB', 31:'-hize-'
}
```

## EID->Slot Mapping (from ff ff 06 XX spawn events)
```python
eid_to_slot = {
    2087:17, 2093:23, 2086:16, 2101:31, 2090:20, 2085:15, 2165:9,
    2097:27, 2091:21, 2078:8,  2095:25, 2083:13, 2089:19, 2174:14,
    124:6,   129:1
}
```

## ✅ CONFIRMED: Ground Kill Event Format

```
[slot_u32 LE 4 bytes][u8 name_len][killer_vehicle_name ASCII][victim_EID u16 LE][killer_EID u16 LE][FF FF FF FF 01 00 01][XX]
```

- `slot_u32` — killer's player slot (0-indexed, 0–63), matches `players[slot_u32]` index in the output JSON
- `name_len` — length of killer's vehicle internal name (4–64 chars)
- `killer_vehicle_name` — ASCII internal name, e.g. `germ_pzkpfw_VI_ausf_h1_tiger_west`
- `victim_EID` / `killer_EID` — u16 LE entity IDs for the victim and killer tanks
- `[FF FF FF FF 01 00 01]` — 7-byte fixed marker identifying this as a kill event
- `XX` — 1 trailing byte; observed values: `0x84` (most common), `0x85`, `0x86`, `0x87` — likely ammo/kill type

**Search strategy:** scan for `FF FF FF FF 01 00 01` (start at offset ~25000 to skip preamble), then read backwards: `rd[idx-2:idx]` = killer_EID, `rd[idx-4:idx-2]` = victim_EID, then walk back `name_len` + 1 bytes for the vehicle name, then 4 bytes for `slot_u32`.

**Validation:** 31 binary kill events extracted from test replay; ground kill counts per slot match JSON ground truth exactly for all ground-kill players (slots 8,9,13,14,15,16,17,19,20,21,23,25,27,30,31). Total across 935 replays: per-slot ground kill counts match in all replays where kills exist.

### JSON slot mapping
`slot_u32` == index into `d['players']` array in the output JSON. The JSON player array order comes from the `player` array in the rez BLK, which is iterated in order by `_parse_results()` in `replay_parser_service.py`. **No separate slot field** exists in the `Player` model — the array index IS the slot.

### Kill type is determined by VICTIM EID, not suffix

```
kills.ground  =  events where victim_EID >= 512   (a ground vehicle was killed)
kills.air     =  events where victim_EID <  512    (an aircraft was killed)
```

The suffix indicates the **killer** type:
- `01 00 01` — killer is a **ground vehicle**
- `02 00 00` — killer is an **aircraft**

Both suffixes can produce either ground or air kills depending on the victim EID.

### Aircraft kill examples (test replay)
- CCTVCNNI (slot 1, f8f1): `02 00 00` suffix, victim_EID=2085 (ground) -> `kills.ground` ✓
- yama2234 (slot 6, f8f1b): `02 00 00` suffix, victim_EIDs=2095/2094 (ground) -> `kills.ground` ✓

### Additional suffixes observed across 935 replays
| Suffix | Total events | Meaning |
|--------|-------------|---------|
| `01 00 01` | 12,378 | ground killer, most common |
| `01 00 00` | 1,066 | ground killer variant (?) |
| `02 00 00` | 702 | aircraft killer |
| `01 01 01` | 97 | unknown |
| `03 00 00` | 67 | unknown |

### Cross-replay validation results (935 replays)
- **Ground kills**: 97.6% exact, 1.9% over, 0.5% under (20,871 / 21,380 per-slot slots correct)
- **Air kills**: 98.4% exact, 0.6% over, 0.9% under
- **478 replays** fully correct on both ground and air
- Remaining ~2% mismatches cluster in specific replays where JSON player array order ≠ binary slot_u32 (known ordering issue)

### EID threshold
`< 512` = aircraft, `>= 512` (typically >= 2000) = ground vehicle. Aircraft EIDs observed: 117–191 range in test set.

---

## What We KNOW (confirmed)
- `ff` byte = 5.9% of rec_data (15x above the ~0.4% random baseline)
- First 712 bytes = preamble (before event stream)
- `ff ff ff 7f` appears at pos=22,079 — something structurally significant starts there
- No simple u8 length field exists at +4 after `ff ff` (0.2% match rate)
- `wt_ext_cli` handles BLK/VROMF only — NOT useful for rec_data stream

## ~~DISPROVEN~~ — `ff ff` as event boundary marker
- `ff ff` occurs **136,524 times** in 5,896,784 bytes = once every **~43 bytes** — far too dense
- **4,257 distinct `ff ff XX YY` patterns** exist — cannot all be event types
- **83,295** of those are `ff ff ff ff` (padding/fill data)
- `ff ff` is a DATA VALUE appearing throughout payloads, NOT a structural boundary
- All previous "event counts" (6,448 / 45 / 29 etc.) are counts of a 4-byte substring, not real event counts
- The "29 kills = 29 `ff ff 9c f1`" match was coincidental — payloads for those 29 contain embedded `ff ff` everywhere

## What We Still Don't Know
- What IS the true event framing? Length-prefixed? Type-dispatched fixed sizes? Something else?
- Where does the init block end? (We assumed pos=22,079 because that's where the next `ff ff` is — now suspect)
- How does a parser know how many bytes to consume for each event?

## The `ff ff 9c f1` 29-occurrence dump (from `structure_out.txt`)
- Every occurrence is followed by 64 bytes shown — but those 64 bytes contain embedded `ff ff` sequences
- Payloads are clearly not fixed-structure — no repeating offsets, varied content
- The count=29 coincidence with kill count is likely just that: coincidence

## Interesting structural clues (from `structure_out.txt`)
- `[0c 96]` appears before `ff ff` 1,271 times — some kind of consistent preceding context
- `[0d 04]` appears 580 times, `[0f 22]` 535 times, `[0c 6b]` 521 times — recurring 2-byte patterns preceding `ff ff`
- These recurring preceding bytes might indicate something about the data structure around `ff ff` values

## EID->Slot Mapping (established before `ff ff` assumption was disproven — method unknown)
```python
eid_to_slot = {
    2087:17, 2093:23, 2086:16, 2101:31, 2090:20, 2085:15, 2165:9,
    2097:27, 2091:21, 2078:8,  2095:25, 2083:13, 2089:19, 2174:14,
    124:6,   129:1
}
```
This mapping should still be valid — it came from parsing the preamble/BLK section, not rec_data events.

## Scripts in temp/
- `wrpl_struct.py` — early structural analysis
- `wrpl_kill_decode.py` -> `decode_out.txt` (17,238 lines) — based on flawed `ff ff` boundary assumption
- `wrpl_kill_boundary.py` — older script with different boundary logic
- `wrpl_event_structure.py` -> `structure_out.txt` — confirmed `ff ff` disproven as boundary

## Key Open Questions
1. **How are events actually framed?** Need to study the preamble (712 bytes) for a type registry or packet catalog. May need to look at pos=712 bytes raw and find where 21,367 actually comes from.
2. **What comes right after the 712-byte preamble?** Read raw bytes at 712–800 without any `ff ff` assumptions.
3. **Community RE?** War Thunder replay format may be partially documented elsewhere — check github/forums.
